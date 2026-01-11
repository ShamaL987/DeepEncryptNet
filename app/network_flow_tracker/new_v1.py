from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Dict, Tuple


FlowKey = Tuple[str, str, str, str, str]


class OffsetStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> int:
        if not self.path.exists():
            return 0
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f).get("offset", 0)

    def save(self, offset: int) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump({"offset": offset}, f)

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()


class StreamFileWriter:
    def __init__(self, stream_id: str, base_dir: Path, header: list[str]):
        self.stream_id = stream_id
        self.path = base_dir / f"{stream_id}.csv"
        self.file = self.path.open("w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)
        self.writer.writerow(header)
        self.file.flush()
        print(f"[STREAM-OPEN] {self.stream_id}")

    def append(self, row: list[str]) -> None:
        self.writer.writerow(row)
        self.file.flush()

    def close(self) -> None:
        self.file.flush()
        self.file.close()
        print(f"[STREAM-CLOSE] {self.stream_id}")


class ActiveStream:
    def __init__(self, stream_id: str, writer: StreamFileWriter, last_seen_ts: float):
        self.stream_id = stream_id
        self.writer = writer
        self.last_seen_ts = last_seen_ts


class PacketStreamDivider:
    def __init__(
        self,
        packet_csv: Path,
        output_dir: Path,
        offset_file: Path,
        start_mode: str,
        idle_timeout_sec: float = 30.0,
        poll_interval_sec: float = 1.0,
    ):
        self.packet_csv = packet_csv
        self.output_dir = output_dir
        self.offset_store = OffsetStore(offset_file)
        self.start_mode = start_mode
        self.idle_timeout_sec = idle_timeout_sec
        self.poll_interval_sec = poll_interval_sec

        self.active_streams: Dict[FlowKey, ActiveStream] = {}
        self.stream_counter = 0

        self.output_dir.mkdir(parents=True, exist_ok=True)

        if self.start_mode == "replay":
            self.offset_store.reset()

        print(f"[INIT] Mode={self.start_mode}")
        print(f"[INIT] Packet CSV={self.packet_csv}")
        print(f"[INIT] Streams Dir={self.output_dir}")

    @staticmethod
    def canonical_flow_key(
        src_ip: str,
        src_port: str,
        dst_ip: str,
        dst_port: str,
        transport: str,
    ) -> FlowKey:
        a = (src_ip, src_port)
        b = (dst_ip, dst_port)
        lo, hi = sorted([a, b])
        return lo[0], lo[1], hi[0], hi[1], transport

    def _new_stream_id(self) -> str:
        self.stream_counter += 1
        return f"stream_{self.stream_counter:06d}"

    def _get_or_create_stream(
        self,
        key: FlowKey,
        header: list[str],
        timestamp: float,
    ) -> ActiveStream:
        if key in self.active_streams:
            return self.active_streams[key]

        stream_id = self._new_stream_id()
        writer = StreamFileWriter(stream_id, self.output_dir, header)
        stream = ActiveStream(stream_id, writer, timestamp)
        self.active_streams[key] = stream

        print(f"[STREAM-CREATE] {stream_id} | {key}")
        return stream

    def _expire_idle_streams(self, now_ts: float) -> None:
        expired = [
            key
            for key, stream in self.active_streams.items()
            if (now_ts - stream.last_seen_ts) > self.idle_timeout_sec
        ]

        for key in expired:
            stream = self.active_streams.pop(key)
            stream.writer.close()

    def run(self) -> None:
        last_offset = (
            0 if self.start_mode == "replay"
            else self.offset_store.load()
        )

        while True:
            if not self.packet_csv.exists():
                print("[WAIT] CSV not found")
                time.sleep(self.poll_interval_sec)
                continue

            with self.packet_csv.open("r", newline="", encoding="utf-8") as f:
                f.seek(last_offset)
                reader = csv.reader(f)

                header = next(reader, None)
                if header is None:
                    time.sleep(self.poll_interval_sec)
                    continue

                processed = 0

                for row in reader:
                    if not row:
                        continue

                    record = dict(zip(header, row))
                    timestamp = float(record["timestamp"])

                    flow_key = self.canonical_flow_key(
                        record["src_ip"],
                        record["src_port"],
                        record["dst_ip"],
                        record["dst_port"],
                        record["transport"],
                    )

                    stream = self._get_or_create_stream(
                        flow_key,
                        header,
                        timestamp,
                    )

                    stream.writer.append(row)
                    stream.last_seen_ts = timestamp
                    processed += 1

                last_offset = f.tell()
                self.offset_store.save(last_offset)

                if processed:
                    print(f"[READ] {processed} packets")

            self._expire_idle_streams(time.time())
            time.sleep(self.poll_interval_sec)
