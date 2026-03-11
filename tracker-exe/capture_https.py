from __future__ import annotations

import csv
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

# =========================
# CONFIGURATION
# =========================

BPF_FILTER = "tcp port 443 or udp port 443"
SCHEMA_VERSION = "v1"

ROTATE_EVERY_SECONDS = 30        # batch duration
ROTATE_MAX_PACKETS = 100        # batch size

FIELD_SEPARATOR = "\t"


CSV_COLUMNS = [
    "timestamp",
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


# =========================
# PATHS
# =========================

class CapturePaths:
    def __init__(self, base_dir: Path):
        self.base = base_dir /"files"/"captures"
        self.writing = self.base / "writing"
        self.ready = self.base / "ready"

    def initialize(self) -> None:
        self.writing.mkdir(parents=True, exist_ok=True)
        self.ready.mkdir(parents=True, exist_ok=True)

# =========================
# TSHARK DISCOVERY
# =========================

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


# =========================
# INTERFACE RESOLUTION
# =========================

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


# =========================
# TSHARK COMMAND
# =========================

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


# =========================
# PACKET PARSER
# =========================

class PacketParser:
    @staticmethod
    def parse(line: str) -> Optional[list[str]]:
        parts = line.rstrip("\n").split(FIELD_SEPARATOR)
        if len(parts) != len(TSHARK_FIELDS):
            return None

        (
            ts,
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
            src_ip,
            src_port,
            dst_ip,
            dst_port,
            transport,
            proto,
            length,
        ]


# =========================
# ROTATING CSV WRITER
# =========================

class RotatingPacketWriter:
    def __init__(
        self,
        paths: CapturePaths,
        rotate_interval_sec: int = 30
    ):
        self.paths = paths
        self.rotate_interval_sec = rotate_interval_sec
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
        self.writer.writerow([
            "timestamp",
            "src_ip",
            "src_port",
            "dst_ip",
            "dst_port",
            "transport",
            "app_protocol",
            "packet_length",
        ])

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

        if (
           (now - self.start_time) >= self.rotate_interval_sec
        ):
            self._open_new_batch()

    def close(self) -> None:
        if self.file:
            self._close_batch()

# =========================
# CAPTURE SESSION
# =========================

class CaptureSession:
    def __init__(self, command: list[str], writer: RotatingPacketWriter):
        self.command = command
        self.writer = writer
        self.running = True

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



# =========================
# ENTRYPOINT
# =========================

def resolve_base_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def main() -> None:
    base_dir = resolve_base_directory()
    paths = CapturePaths(base_dir)
    paths.initialize()

    tshark = TsharkLocator.locate()
    iface = NetworkInterfaceResolver(tshark).resolve()
    command = TsharkCommandFactory.build(tshark, iface)

    writer = RotatingPacketWriter(paths)
    CaptureSession(command, writer).start()



if __name__ == "__main__":
    main()
