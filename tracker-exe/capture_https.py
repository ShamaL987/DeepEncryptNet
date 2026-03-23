from __future__ import annotations

import csv
import json
import platform
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

import requests

BPF_FILTER = "tcp port 443 or udp port 443"
SCHEMA_VERSION = "v1"

ROTATE_EVERY_SECONDS = 60
ROTATE_MAX_PACKETS = 10000
UPLOAD_POLL_INTERVAL_SECONDS = 2
REQUEST_TIMEOUT_SECONDS = 60

FIELD_SEPARATOR = "\t"
CONFIG_FILE_NAME = "deepencryptnet_client_config.json"
DEFAULT_UPLOAD_PATH = "api/file-upload/ingest"

CSV_COLUMNS = [
    "timestamp",
    "frame_number",
    "src_ip",
    "src_port",
    "dst_ip",
    "dst_port",
    "transport",
    "app_protocol",
    "packet_length",
]

TSHARK_FIELDS = [
    "frame.time_epoch",
    "frame.number",
    "ip.src",
    "ipv6.src",
    "tcp.srcport",
    "udp.srcport",
    "ip.dst",
    "ipv6.dst",
    "tcp.dstport",
    "udp.dstport",
    "_ws.col.Protocol",
    "frame.len",
]


class CapturePaths:
    def __init__(self, base_dir: Path):
        self.base = base_dir / "files" / "captures"
        self.writing = self.base / "writing"
        self.ready = self.base / "ready"
        self.sent = self.base / "sent"

    def initialize(self) -> None:
        self.writing.mkdir(parents=True, exist_ok=True)
        self.ready.mkdir(parents=True, exist_ok=True)
        self.sent.mkdir(parents=True, exist_ok=True)


class AppConfig:
    def __init__(self, base_dir: Path):
        self.path = base_dir / CONFIG_FILE_NAME

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> dict:
        if not self.exists():
            raise RuntimeError("Configuration file does not exist")
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_or_prompt(self) -> dict:
        if self.exists():
            data = self.load()
            if data.get("server_url") and data.get("api_token"):
                return data

        server_url = input("Enter server URL: ").strip().rstrip("/")
        while not server_url:
            print("Server URL is required")
            server_url = input("Enter server URL: ").strip().rstrip("/")

        api_token = input("Enter API token: ").strip()
        while not api_token:
            print("API token is required")
            api_token = input("Enter API token: ").strip()

        data = {
            "schema_version": SCHEMA_VERSION,
            "server_url": server_url,
            "api_token": api_token,
            "upload_path": DEFAULT_UPLOAD_PATH,
        }
        self.save(data)
        return data


class TsharkLocator:
    @staticmethod
    def locate() -> Path:
        env = shutil.which("tshark")
        if env:
            return Path(env)

        system = platform.system().lower()
        candidates = {
            "windows": [
                Path(r"C:\Program Files\Wireshark\tshark.exe"),
                Path(r"C:\Program Files (x86)\Wireshark\tshark.exe"),
            ],
            "linux": [
                Path("/usr/bin/tshark"),
                Path("/usr/sbin/tshark"),
            ],
            "darwin": [
                Path("/usr/local/bin/tshark"),
                Path("/opt/homebrew/bin/tshark"),
            ],
        }.get(system, [])

        for path in candidates:
            if path.exists():
                return path

        raise RuntimeError("tshark executable not found")


class NetworkInterfaceResolver:
    def __init__(self, tshark_path: Path):
        self.tshark_path = tshark_path

    def list_interfaces(self) -> list[tuple[int, str]]:
        out = subprocess.check_output(
            [self.tshark_path, "-D"],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        interfaces = []
        for line in out.splitlines():
            try:
                idx, name = line.split(".", 1)
                interfaces.append((int(idx.strip()), name.strip()))
            except ValueError:
                continue
        return interfaces

    def validate(self, index: int) -> bool:
        try:
            proc = subprocess.run(
                [
                    self.tshark_path,
                    "-i", str(index),
                    "-f", BPF_FILTER,
                    "-a", "duration:1",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            return proc.returncode == 0
        except subprocess.TimeoutExpired:
            return False

    def resolve(self) -> int:
        interfaces = self.list_interfaces()
        if not interfaces:
            raise RuntimeError("No network interfaces found")

        print("\nAvailable interfaces:")
        for idx, name in interfaces:
            print(f"{idx}. {name}")

        while True:
            choice = input("\nSelect interface number: ").strip()
            if not choice.isdigit():
                print("Invalid input")
                continue

            idx = int(choice)
            if not any(i == idx for i, _ in interfaces):
                print("Not in list")
                continue

            if self.validate(idx):
                print(f"[CAPTURE] Using interface {idx}")
                return idx

            print("Interface not usable")


class TsharkCommandFactory:
    @staticmethod
    def build(tshark_path: Path, interface_index: int) -> list[str]:
        cmd = [
            str(tshark_path),
            "-i", str(interface_index),
            "-f", BPF_FILTER,
            "-l",
            "-T", "fields",
            "-E", f"separator={FIELD_SEPARATOR}",
            "-E", "header=n",
        ]
        for f in TSHARK_FIELDS:
            cmd.extend(["-e", f])
        return cmd


class PacketParser:
    @staticmethod
    def parse(line: str) -> Optional[list[str]]:
        parts = line.rstrip("\n").split(FIELD_SEPARATOR)
        if len(parts) != len(TSHARK_FIELDS):
            return None

        (
            ts,
            frame_number,
            ipv4_src, ipv6_src,
            tcp_src, udp_src,
            ipv4_dst, ipv6_dst,
            tcp_dst, udp_dst,
            proto,
            length,
        ) = parts

        src_ip = ipv4_src or ipv6_src
        dst_ip = ipv4_dst or ipv6_dst

        if tcp_src or tcp_dst:
            src_port, dst_port = tcp_src, tcp_dst
            transport = "tcp"
        elif udp_src or udp_dst:
            src_port, dst_port = udp_src, udp_dst
            transport = "udp"
        else:
            return None

        return [
            ts,
            frame_number,
            src_ip,
            src_port,
            dst_ip,
            dst_port,
            transport,
            proto,
            length,
        ]


class RotatingPacketWriter:
    def __init__(
        self,
        paths: CapturePaths,
        rotate_interval_sec: int = ROTATE_EVERY_SECONDS,
        rotate_max_packets: int = ROTATE_MAX_PACKETS,
    ):
        self.paths = paths
        self.rotate_interval_sec = rotate_interval_sec
        self.rotate_max_packets = rotate_max_packets
        self.capture_session_id = self._generate_capture_session_id()

        self.batch_id = 0
        self.packet_count = 0
        self.start_time = time.time()

        self.file = None
        self.writer = None
        self.current_tmp = None

        self._open_new_batch()

    @staticmethod
    def _generate_capture_session_id() -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uid = uuid4().hex[:8]
        return f"capture_{ts}_{short_uid}"

    def _open_new_batch(self) -> None:
        if self.file:
            self._close_batch()

        self.batch_id += 1
        self.packet_count = 0
        self.start_time = time.time()

        self.current_tmp = self.paths.writing / (
            f"{self.capture_session_id}_batch_{self.batch_id:05d}.tmp"
        )
        self.file = self.current_tmp.open("w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)
        self.writer.writerow(CSV_COLUMNS)

    def _close_batch(self) -> None:
        self.file.flush()
        self.file.close()

        final_csv = self.paths.ready / self.current_tmp.with_suffix(".csv").name
        self.current_tmp.replace(final_csv)

        print(f"[CAPTURE] Closed batch → {final_csv}")

    def write_row(self, row: list[str]) -> None:
        now = time.time()
        self.writer.writerow(row)
        self.packet_count += 1

        should_rotate_by_time = (now - self.start_time) >= self.rotate_interval_sec
        should_rotate_by_packets = self.packet_count >= self.rotate_max_packets

        if should_rotate_by_time or should_rotate_by_packets:
            self._open_new_batch()

    def close(self) -> None:
        if self.file:
            self._close_batch()


class UploadClient:
    def __init__(self, server_url: str, api_token: str, upload_path: str):
        self.server_url = server_url.rstrip("/")
        self.api_token = api_token
        self.upload_path = upload_path if upload_path.startswith("/") else f"/{upload_path}"

    @property
    def upload_url(self) -> str:
        return f"{self.server_url}{self.upload_path}"

    def upload_csv(self, csv_path: Path) -> dict:
        with csv_path.open("rb") as file_handle:
            response = requests.post(
                self.upload_url,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                },
                files={
                    "file": (csv_path.name, file_handle, "text/csv"),
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

        if not response.ok:
            raise RuntimeError(
                f"Upload failed for {csv_path.name}: {response.status_code} {response.text}"
            )

        return response.json()


class ReadyDirectoryUploader:
    def __init__(self, paths: CapturePaths, client: UploadClient):
        self.paths = paths
        self.client = client
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            ready_files = sorted(self.paths.ready.glob("*.csv"))

            for csv_path in ready_files:
                if self._stop_event.is_set():
                    break

                try:
                    result = self.client.upload_csv(csv_path)
                    target_path = self.paths.sent / csv_path.name
                    csv_path.replace(target_path)
                    print(f"[UPLOAD] Sent {csv_path.name} → {result.get('status')}")
                except Exception as exc:
                    print(f"[UPLOAD] Failed {csv_path.name}: {exc}")
                    time.sleep(UPLOAD_POLL_INTERVAL_SECONDS)
                    break

            time.sleep(UPLOAD_POLL_INTERVAL_SECONDS)


class CaptureSession:
    def __init__(self, command: list[str], writer: RotatingPacketWriter):
        self.command = command
        self.writer = writer

    def start(self) -> None:
        proc = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

        try:
            for line in proc.stdout:
                parsed = PacketParser.parse(line)
                if parsed:
                    self.writer.write_row(parsed)
        finally:
            self.writer.close()
            proc.terminate()


def resolve_base_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def main() -> None:
    base_dir = resolve_base_directory()
    paths = CapturePaths(base_dir)
    paths.initialize()

    config_store = AppConfig(base_dir)
    app_config = config_store.load_or_prompt()

    upload_client = UploadClient(
        server_url=app_config["server_url"],
        api_token=app_config["api_token"],
        upload_path=app_config.get("upload_path", DEFAULT_UPLOAD_PATH),
    )

    uploader = ReadyDirectoryUploader(paths, upload_client)
    uploader_thread = threading.Thread(target=uploader.run, daemon=True)
    uploader_thread.start()

    tshark = TsharkLocator.locate()
    iface = NetworkInterfaceResolver(tshark).resolve()
    command = TsharkCommandFactory.build(tshark, iface)

    writer = RotatingPacketWriter(paths)

    try:
        CaptureSession(command, writer).start()
    except KeyboardInterrupt:
        print("\n[APP] Stopping capture")
    finally:
        uploader.stop()


if __name__ == "__main__":
    main()