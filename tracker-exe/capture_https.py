from __future__ import annotations

import csv
import platform
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional


BPF_FILTER = "tcp port 443 or udp port 443"
SCHEMA_VERSION = "v1"

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

FIELD_SEPARATOR = "\t"


class CapturePaths:
    def __init__(self, base_dir: Path):
        self.capture_dir = base_dir / "captures"
        self.output_csv = self.capture_dir / f"live_https_{SCHEMA_VERSION}.csv"

    def initialize(self) -> None:
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        if not self.output_csv.exists():
            with self.output_csv.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(CSV_COLUMNS)


class TsharkLocator:
    @staticmethod
    def locate() -> Path:
        env_path = shutil.which("tshark")
        if env_path:
            return Path(env_path)

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

        for candidate in candidates:
            if candidate.exists():
                return candidate

        raise RuntimeError("tshark executable not found")


class NetworkInterfaceResolver:
    def __init__(self, tshark_path: Path):
        self.tshark_path = tshark_path

    def list_interfaces(self) -> list[tuple[int, str]]:
        output = subprocess.check_output(
            [self.tshark_path, "-D"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        interfaces = []
        for line in output.splitlines():
            try:
                index, name = line.split(".", 1)
                interfaces.append((int(index.strip()), name.strip()))
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

        print("\nAvailable network interfaces:")
        for index, name in interfaces:
            print(f"{index}. {name}")

        while True:
            choice = input("\nSelect interface number: ").strip()
            if not choice.isdigit():
                print("Invalid input")
                continue

            index = int(choice)
            if not any(i == index for i, _ in interfaces):
                print("Interface not in list")
                continue

            if self.validate(index):
                print(f"[CAPTURE] Selected interface {index}")
                return index

            print("Selected interface cannot be used")


class TsharkCommandFactory:
    @staticmethod
    def build(tshark_path: Path, interface_index: int) -> list[str]:
        command = [
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
            command.extend(["-e", field])
        return command


class PacketParser:
    @staticmethod
    def parse(line: str) -> Optional[list[str]]:
        parts = line.rstrip("\n").split(FIELD_SEPARATOR)
        if len(parts) != len(TSHARK_FIELDS):
            return None

        (
            timestamp,
            ipv4_src,
            ipv6_src,
            tcp_src,
            udp_src,
            ipv4_dst,
            ipv6_dst,
            tcp_dst,
            udp_dst,
            app_protocol,
            packet_length,
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
            timestamp,
            src_ip,
            src_port,
            dst_ip,
            dst_port,
            transport,
            app_protocol,
            packet_length,
        ]


class BufferedPacketWriter:
    def __init__(self, output_csv: Path, flush_interval: int = 50):
        self.output_csv = output_csv
        self.flush_interval = flush_interval
        self.buffer: list[list[str]] = []
        self.file = self.output_csv.open("a", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)

    def write_row(self, row: list[str]) -> None:
        self.buffer.append(row)
        print("[PACKET]", row)

        if len(self.buffer) >= self.flush_interval:
            self.flush()

    def flush(self) -> None:
        if self.buffer:
            self.writer.writerows(self.buffer)
            self.file.flush()
            self.buffer.clear()

    def close(self) -> None:
        self.flush()
        self.file.close()


class CaptureSession:
    def __init__(self, command: list[str], writer: BufferedPacketWriter):
        self.command = command
        self.writer = writer
        self.process: Optional[subprocess.Popen[str]] = None
        self.running = True

    def start(self) -> None:
        print("[CAPTURE] Starting capture")
        self.process = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        try:
            assert self.process.stdout
            for line in self.process.stdout:
                if not self.running:
                    break
                parsed = PacketParser.parse(line)
                if parsed:
                    self.writer.write_row(parsed)
        finally:
            self.stop()

    def stop(self, *_):
        if not self.running:
            return
        print("[CAPTURE] Stopping capture")
        self.running = False

        if self.process and self.process.poll() is None:
            self.process.terminate()

        self.writer.close()


def resolve_base_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def main() -> None:
    base_dir = resolve_base_directory()
    paths = CapturePaths(base_dir)
    paths.initialize()

    tshark_path = TsharkLocator.locate()
    interface_index = NetworkInterfaceResolver(tshark_path).resolve()

    command = TsharkCommandFactory.build(tshark_path, interface_index)
    writer = BufferedPacketWriter(paths.output_csv)

    CaptureSession(command, writer).start()


if __name__ == "__main__":
    main()
