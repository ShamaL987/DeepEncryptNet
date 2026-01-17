from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Dict, Tuple, Optional

from app.network_flow_tracker.stream_feature_extractor import StreamFeatureExtractor
from app.pipeline.prediction_queue import PredictionQueue

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
        print(f"[STREAM-OPEN] {self.stream_id}", flush=True)

    def append(self, row: list[str]) -> None:
        self.writer.writerow(row)
        self.file.flush()

    def close(self) -> None:
        self.file.flush()
        self.file.close()
        print(f"[STREAM-CLOSE] {self.stream_id}", flush=True)


class ActiveStream:
    def __init__(
        self,
        stream_id: str,
        writer: StreamFileWriter,
        last_seen_ts: float,
        last_seen_wall: float,
    ):
        self.stream_id = stream_id
        self.writer = writer
        self.last_seen_ts = last_seen_ts
        self.last_seen_wall = last_seen_wall
        self.features_extracted = False


class PacketStreamDivider:
    def __init__(
        self,
        packet_csv: Path,
        output_dir: Path,
        offset_file: Path,
        start_mode: str,
        extract_features: bool,
        prediction_queue: PredictionQueue,
        idle_timeout_sec: float = 30.0,
        poll_interval_sec: float = 1.0,
    ):
        self.packet_csv = packet_csv
        self.output_dir = output_dir
        self.offset_store = OffsetStore(offset_file)
        self.start_mode = start_mode
        self.extract_features = extract_features
        self.idle_timeout_sec = idle_timeout_sec
        self.poll_interval_sec = poll_interval_sec

        self.active_streams: Dict[FlowKey, ActiveStream] = {}
        self.stream_counter = 0

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.enable_prediction = True
        self.prediction_queue = prediction_queue

        if self.start_mode == "replay":
            self.offset_store.reset()

        self.extractor = StreamFeatureExtractor(idle_threshold=1.0)

        print(f"[INIT] Mode={self.start_mode}", flush=True)
        print(f"[INIT] ExtractFeatures={self.extract_features}", flush=True)
        print(f"[INIT] Packet CSV={self.packet_csv}", flush=True)
        print(f"[INIT] Streams Dir={self.output_dir}", flush=True)

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

    @staticmethod
    def _parse_epoch_timestamp(value: Optional[str]) -> Optional[float]:
        try:
            if value is None:
                return None
            ts = float(value.strip())
            return ts if ts > 0 else None
        except (ValueError, TypeError):
            return None

    def _new_stream_id(self) -> str:
        self.stream_counter += 1
        return f"stream_{self.stream_counter:06d}"

    def _finalize_stream(self, stream: ActiveStream) -> None:
        stream.writer.close()

        if self.extract_features and not stream.features_extracted:
            features = self.extractor.extract(stream.writer.path, stream.stream_id)
            if features:
                print(f"[FEATURES] extracted for {stream.stream_id}", flush=True)
                print(features, flush=True)
            stream.features_extracted = True
            if self.enable_prediction:
                self.prediction_queue.enqueue(stream.stream_id)

    def _get_or_create_stream(
        self,
        key: FlowKey,
        header: list[str],
        timestamp: float,
    ) -> ActiveStream:
        existing = self.active_streams.get(key)
        now_wall = time.time()

        if existing:
            if (timestamp - existing.last_seen_ts) > self.idle_timeout_sec:
                print(f"[STREAM-SPLIT] {existing.stream_id}", flush=True)
                self._finalize_stream(existing)
                del self.active_streams[key]
            else:
                return existing

        stream_id = self._new_stream_id()
        writer = StreamFileWriter(stream_id, self.output_dir, header)
        stream = ActiveStream(stream_id, writer, timestamp, now_wall)
        self.active_streams[key] = stream

        print(f"[STREAM-CREATE] {stream_id} | {key}", flush=True)
        return stream

    def _expire_idle_streams_wallclock(self) -> None:
        now = time.time()
        expired = [
            key for key, stream in self.active_streams.items()
            if (now - stream.last_seen_wall) > self.idle_timeout_sec
        ]

        for key in expired:
            stream = self.active_streams.pop(key)
            print(f"[STREAM-IDLE-CLOSE] {stream.stream_id}", flush=True)
            self._finalize_stream(stream)

    def run(self, stop_event) -> None:
        last_offset = 0 if self.start_mode == "replay" else self.offset_store.load()

        while True:
            if stop_event and stop_event.is_set():
                print("[FLOW] Stop signal received", flush=True)
                break

            if self.start_mode == "live":
                self._expire_idle_streams_wallclock()
                # print(f"[LIVE-HEARTBEAT] {time.time():.2f}", flush=True)

            if not self.packet_csv.exists():
                print("[WAIT] CSV not found", flush=True)
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
                    timestamp = self._parse_epoch_timestamp(record.get("timestamp"))
                    if timestamp is None:
                        continue

                    flow_key = self.canonical_flow_key(
                        record["src_ip"],
                        record["src_port"],
                        record["dst_ip"],
                        record["dst_port"],
                        record["transport"],
                    )

                    stream = self._get_or_create_stream(flow_key, header, timestamp)

                    stream.writer.append(row)
                    stream.last_seen_ts = timestamp
                    stream.last_seen_wall = time.time()
                    processed += 1

                new_offset = f.tell()
                self.offset_store.save(new_offset)

                if processed:
                    print(f"[READ] {processed} packets", flush=True)

                if self.start_mode == "replay" and new_offset == last_offset:
                    for stream in list(self.active_streams.values()):
                        self._finalize_stream(stream)
                    self.active_streams.clear()
                    print("[REPLAY] All streams finalized", flush=True)
                    return

                last_offset = new_offset

            time.sleep(self.poll_interval_sec)
