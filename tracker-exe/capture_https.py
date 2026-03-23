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
from urllib.parse import urlparse
from uuid import uuid4

import requests

BPF_FILTER = "tcp port 443 or udp port 443"
SCHEMA_VERSION = "v1"

ROTATE_EVERY_SECONDS = 60
ROTATE_MAX_PACKETS = 10000
UPLOAD_POLL_INTERVAL_SECONDS = 2
REQUEST_TIMEOUT_SECONDS = 60
LIVE_STATUS_PRINT_INTERVAL_SECONDS = 2

FIELD_SEPARATOR = "\t"
CONFIG_FILE_NAME = "deepencryptnet_client_config.json"
DEFAULT_UPLOAD_PATH = "api/file-upload/ingest"
DEFAULT_VALIDATE_PATH = "api/user/external/validate"

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


def print_header(title: str) -> None:
    line = "=" * 72
    print(f"\n{line}\n{title}\n{line}")


def print_step(message: str) -> None:
    print(f"[STEP] {message}")


def print_info(message: str) -> None:
    print(f"[INFO] {message}")


def print_success(message: str) -> None:
    print(f"[OK]   {message}")


def print_warn(message: str) -> None:
    print(f"[WARN] {message}")


def print_error(message: str) -> None:
    print(f"[ERR]  {message}")


def mask_token(token: str) -> str:
    if len(token) <= 12:
        return token
    return f"{token[:12]}...{token[-8:]}"


def normalize_server_url(raw_url: str) -> str:
    return raw_url.strip().rstrip("/")


def validate_server_url_format(server_url: str) -> tuple[bool, str]:
    if not server_url:
        return False, "Server URL is required"

    parsed = urlparse(server_url)
    if not parsed.scheme or not parsed.netloc:
        return False, "Enter a full URL such as https://your-server.com"

    host = (parsed.hostname or "").lower()
    is_local_host = host in {"localhost", "127.0.0.1", "0.0.0.0"}

    if parsed.scheme != "https" and not is_local_host:
        return False, "Server URL must use HTTPS for remote servers"

    return True, ""


def disable_windows_quick_edit_mode() -> None:
    if platform.system().lower() != "windows":
        return

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-10)
        if handle == 0 or handle == -1:
            return

        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return

        ENABLE_QUICK_EDIT_MODE = 0x0040
        ENABLE_EXTENDED_FLAGS = 0x0080

        new_mode = mode.value
        new_mode |= ENABLE_EXTENDED_FLAGS
        new_mode &= ~ENABLE_QUICK_EDIT_MODE

        kernel32.SetConsoleMode(handle, new_mode)
    except Exception:
        pass


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

    def prompt_server_url(self) -> str:
        while True:
            value = normalize_server_url(input("Enter server URL: "))
            is_valid, reason = validate_server_url_format(value)
            if is_valid:
                return value
            print_warn(reason)

    def prompt_api_token(self) -> str:
        while True:
            value = input("Enter API token: ").strip()
            if value:
                return value
            print_warn("API token is required")

    def prompt_and_save(self) -> dict:
        print_header("DeepEncryptNet Client Setup")
        print_info("Server URL example: https://deepencryptnet-staging.up.railway.app")
        print_info("Paste the API token copied from the DeepEncryptNet dashboard")

        server_url = self.prompt_server_url()
        api_token = self.prompt_api_token()

        data = {
            "schema_version": SCHEMA_VERSION,
            "server_url": server_url,
            "api_token": api_token,
            "upload_path": DEFAULT_UPLOAD_PATH,
            "validate_path": DEFAULT_VALIDATE_PATH,
        }
        self.save(data)
        print_success(f"Configuration saved to: {self.path}")
        return data

    def load_or_prompt(self) -> dict:
        if not self.exists():
            return self.prompt_and_save()

        try:
            data = self.load()
        except Exception:
            print_warn("Existing configuration file could not be read")
            return self.prompt_and_save()

        if not data.get("server_url") or not data.get("api_token"):
            print_warn("Existing configuration is incomplete")
            return self.prompt_and_save()

        print_header("DeepEncryptNet Client Configuration")
        print_info(f"Config file : {self.path}")
        print_info(f"Server URL  : {data['server_url']}")
        print_info(f"API Token   : {mask_token(data['api_token'])}")

        reuse = input("Reuse saved configuration? [Y/n]: ").strip().lower()
        if reuse in {"", "y", "yes"}:
            return data

        return self.prompt_and_save()


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
                    "-i",
                    str(index),
                    "-f",
                    BPF_FILTER,
                    "-a",
                    "duration:1",
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

        print_header("Available Network Interfaces")
        print_info(f"Capture filter: {BPF_FILTER}")
        for idx, name in interfaces:
            print(f"{idx:>2}. {name}")

        while True:
            choice = input("\nSelect interface number: ").strip()
            if not choice.isdigit():
                print_warn("Please enter a valid interface number")
                continue

            idx = int(choice)
            if not any(i == idx for i, _ in interfaces):
                print_warn("Selected interface is not in the list")
                continue

            print_step(f"Validating interface {idx}...")
            if self.validate(idx):
                print_success(f"Using interface {idx}")
                return idx

            print_warn("Selected interface is not usable for capture")


class TsharkCommandFactory:
    @staticmethod
    def build(tshark_path: Path, interface_index: int) -> list[str]:
        cmd = [
            str(tshark_path),
            "-i",
            str(interface_index),
            "-f",
            BPF_FILTER,
            "-l",
            "-T",
            "fields",
            "-E",
            f"separator={FIELD_SEPARATOR}",
            "-E",
            "header=n",
        ]
        for field in TSHARK_FIELDS:
            cmd.extend(["-e", field])
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
            ipv4_src,
            ipv6_src,
            tcp_src,
            udp_src,
            ipv4_dst,
            ipv6_dst,
            tcp_dst,
            udp_dst,
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


class LiveStatus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.capture_session_id = ""
        self.current_batch_id = 0
        self.current_batch_packets = 0
        self.total_captured_packets = 0
        self.total_ready_batches = 0
        self.total_uploaded_files = 0
        self.last_capture_at = 0.0
        self.last_upload_at = 0.0
        self.last_upload_name = ""
        self.last_ready_name = ""

    def set_capture_session(self, capture_session_id: str) -> None:
        with self._lock:
            self.capture_session_id = capture_session_id

    def start_batch(self, batch_id: int) -> None:
        with self._lock:
            self.current_batch_id = batch_id
            self.current_batch_packets = 0

    def mark_capture(self, packet_count: int = 1) -> None:
        with self._lock:
            self.current_batch_packets += packet_count
            self.total_captured_packets += packet_count
            self.last_capture_at = time.time()

    def mark_batch_ready(self, batch_name: str) -> None:
        with self._lock:
            self.total_ready_batches += 1
            self.last_ready_name = batch_name

    def mark_upload(self, file_name: str) -> None:
        with self._lock:
            self.total_uploaded_files += 1
            self.last_upload_at = time.time()
            self.last_upload_name = file_name

    def snapshot(self) -> dict[str, str | int | float]:
        with self._lock:
            return {
                "capture_session_id": self.capture_session_id,
                "current_batch_id": self.current_batch_id,
                "current_batch_packets": self.current_batch_packets,
                "total_captured_packets": self.total_captured_packets,
                "total_ready_batches": self.total_ready_batches,
                "total_uploaded_files": self.total_uploaded_files,
                "last_capture_at": self.last_capture_at,
                "last_upload_at": self.last_upload_at,
                "last_upload_name": self.last_upload_name,
                "last_ready_name": self.last_ready_name,
            }


class LiveConsolePrinter:
    def __init__(
        self,
        status: LiveStatus,
        paths: CapturePaths,
        interval_seconds: int = LIVE_STATUS_PRINT_INTERVAL_SECONDS,
    ) -> None:
        self.status = status
        self.paths = paths
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            snap = self.status.snapshot()
            ready_count = len(list(self.paths.ready.glob("*.csv")))

            print_info(
                "Capturing..."
                f" session={snap['capture_session_id'] or '-'}"
                f" batch={snap['current_batch_id']}"
                f" batch_packets={snap['current_batch_packets']}"
                f" total_packets={snap['total_captured_packets']}"
            )
            print_info(
                "Uploading..."
                f" ready_files={ready_count}"
                f" uploaded_files={snap['total_uploaded_files']}"
                f" last_ready={snap['last_ready_name'] or '-'}"
                f" last_uploaded={snap['last_upload_name'] or '-'}"
            )

            self._stop_event.wait(self.interval_seconds)


class RotatingPacketWriter:
    def __init__(
        self,
        paths: CapturePaths,
        live_status: LiveStatus,
        rotate_interval_sec: int = ROTATE_EVERY_SECONDS,
        rotate_max_packets: int = ROTATE_MAX_PACKETS,
    ):
        self.paths = paths
        self.live_status = live_status
        self.rotate_interval_sec = rotate_interval_sec
        self.rotate_max_packets = rotate_max_packets
        self.capture_session_id = self._generate_capture_session_id()

        self.batch_id = 0
        self.packet_count = 0
        self.start_time = time.time()

        self.file = None
        self.writer = None
        self.current_tmp = None

        self.live_status.set_capture_session(self.capture_session_id)
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
        self.live_status.start_batch(self.batch_id)

    def _close_batch(self) -> None:
        if not self.file or not self.current_tmp:
            return

        self.file.flush()
        self.file.close()

        final_csv = self.paths.ready / self.current_tmp.with_suffix(".csv").name
        self.current_tmp.replace(final_csv)

        self.live_status.mark_batch_ready(final_csv.name)
        print_info(f"Closed batch and moved to ready: {final_csv.name}")

        self.file = None
        self.writer = None
        self.current_tmp = None

    def write_row(self, row: list[str]) -> None:
        if not self.writer:
            return

        now = time.time()
        self.writer.writerow(row)
        self.packet_count += 1
        self.live_status.mark_capture(1)

        should_rotate_by_time = (now - self.start_time) >= self.rotate_interval_sec
        should_rotate_by_packets = self.packet_count >= self.rotate_max_packets

        if should_rotate_by_time or should_rotate_by_packets:
            self._open_new_batch()

    def close(self) -> None:
        if self.file:
            self._close_batch()


class UploadClient:
    def __init__(
        self,
        server_url: str,
        api_token: str,
        upload_path: str,
        validate_path: str,
    ):
        self.server_url = server_url.rstrip("/")
        self.api_token = api_token
        self.upload_path = upload_path if upload_path.startswith("/") else f"/{upload_path}"
        self.validate_path = validate_path if validate_path.startswith("/") else f"/{validate_path}"

    @property
    def upload_url(self) -> str:
        return f"{self.server_url}{self.upload_path}"

    @property
    def validate_url(self) -> str:
        return f"{self.server_url}{self.validate_path}"

    def validate_token(self) -> dict:
        response = requests.get(
            self.validate_url,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if not response.ok:
            raise RuntimeError(
                f"Authentication failed: {response.status_code} {response.text}"
            )

        payload = response.json()
        if not payload.get("valid"):
            raise RuntimeError("Authentication failed: token is not valid")

        return payload

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
    def __init__(self, paths: CapturePaths, client: UploadClient, live_status: LiveStatus):
        self.paths = paths
        self.client = client
        self.live_status = live_status
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def process_ready_files_once(self) -> int:
        uploaded_count = 0
        ready_files = sorted(self.paths.ready.glob("*.csv"))

        for csv_path in ready_files:
            if self._stop_event.is_set():
                break

            result = self.client.upload_csv(csv_path)
            target_path = self.paths.sent / csv_path.name
            csv_path.replace(target_path)
            uploaded_count += 1
            self.live_status.mark_upload(csv_path.name)
            print_success(f"Uploaded {csv_path.name} → {result.get('status')}")

        return uploaded_count

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.process_ready_files_once()
            except Exception as exc:
                print_warn(f"Background upload retry pending: {exc}")

            self._stop_event.wait(UPLOAD_POLL_INTERVAL_SECONDS)


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
            if proc.stdout is None:
                raise RuntimeError("tshark stdout pipe is not available")

            for line in proc.stdout:
                parsed = PacketParser.parse(line)
                if parsed:
                    self.writer.write_row(parsed)
        finally:
            self.writer.close()
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()


def resolve_base_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def build_validated_client(config_store: AppConfig) -> tuple[dict, UploadClient]:
    while True:
        app_config = config_store.load_or_prompt()

        server_url = normalize_server_url(app_config["server_url"])
        is_valid, reason = validate_server_url_format(server_url)
        if not is_valid:
            print_error(reason)
            print_warn("Please re-enter configuration")
            app_config = config_store.prompt_and_save()
            continue

        client = UploadClient(
            server_url=server_url,
            api_token=app_config["api_token"],
            upload_path=app_config.get("upload_path", DEFAULT_UPLOAD_PATH),
            validate_path=app_config.get("validate_path", DEFAULT_VALIDATE_PATH),
        )

        print_header("Server Authentication")
        print_step(f"Validating remote access against: {client.server_url}")

        try:
            payload = client.validate_token()
            user = payload.get("user", {})
            print_success("Authentication successful")
            print_info(f"Authenticated user: {user.get('username')} ({user.get('email')})")
            return app_config, client
        except Exception as exc:
            print_error(str(exc))
            retry = input("Re-enter server URL and token? [Y/n]: ").strip().lower()
            if retry in {"", "y", "yes"}:
                config_store.prompt_and_save()
                continue
            raise


def process_pending_ready_files(paths: CapturePaths, uploader: ReadyDirectoryUploader) -> None:
    pending_files = sorted(paths.ready.glob("*.csv"))

    print_header("Pending Upload Check")
    if not pending_files:
        print_info("No older CSV files found in ready folder")
        return

    print_info(f"Found {len(pending_files)} pending CSV file(s) in ready folder")
    print_step("Uploading pending files before live capture starts...")

    try:
        uploaded_count = uploader.process_ready_files_once()
        print_success(f"Pending upload completed: {uploaded_count} file(s) sent")
    except Exception as exc:
        print_warn(f"Pending upload could not fully complete: {exc}")
        print_warn("Remaining files will stay in ready folder and retry later")


def main() -> None:
    disable_windows_quick_edit_mode()

    print_header("DeepEncryptNet HTTPS Capture Client")

    base_dir = resolve_base_directory()
    paths = CapturePaths(base_dir)
    paths.initialize()

    print_info(f"Base directory : {base_dir}")
    print_info(f"Ready folder   : {paths.ready}")
    print_info(f"Sent folder    : {paths.sent}")

    config_store = AppConfig(base_dir)
    _, upload_client = build_validated_client(config_store)

    live_status = LiveStatus()
    uploader = ReadyDirectoryUploader(paths, upload_client, live_status)
    process_pending_ready_files(paths, uploader)

    print_header("Capture Preparation")
    tshark = TsharkLocator.locate()
    print_success(f"tshark found: {tshark}")

    iface = NetworkInterfaceResolver(tshark).resolve()
    command = TsharkCommandFactory.build(tshark, iface)

    uploader_thread = threading.Thread(target=uploader.run, daemon=True)
    uploader_thread.start()
    print_success("Background uploader started")

    live_printer = LiveConsolePrinter(live_status, paths)
    live_printer_thread = threading.Thread(target=live_printer.run, daemon=True)
    live_printer_thread.start()
    print_success("Live console printer started")

    writer = RotatingPacketWriter(paths, live_status)

    print_header("Live Capture Started")
    print_info("CSV batches will be written to writing/, moved to ready/, and uploaded automatically")
    print_info("The process will keep printing capture/upload status until you close the window or press Ctrl+C")

    try:
        CaptureSession(command, writer).start()
    except KeyboardInterrupt:
        print("\n[APP] Stopping capture")
    finally:
        uploader.stop()
        live_printer.stop()
        uploader_thread.join(timeout=2)
        live_printer_thread.join(timeout=2)


if __name__ == "__main__":
    main()