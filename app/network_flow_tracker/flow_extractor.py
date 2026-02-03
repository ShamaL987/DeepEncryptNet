from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Dict, Tuple, Optional

from app.network_flow_tracker.stream_feature_extractor import StreamFeatureExtractor
from app.pipeline.prediction_queue import PredictionQueue


FlowKey = Tuple[str, str, str, str, str]


class StreamFileWriter:
    def __init__(self, stream_id: str, base_dir: Path, header: list[str]):
        self.path = base_dir / f"{stream_id}.csv"
        self.file = self.path.open("w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)
        self.writer.writerow(header)

    def append(self, row: list[str]) -> None:
        self.writer.writerow(row)

    def close(self) -> None:
        self.file.flush()
        self.file.close()


class ActiveStream:
    def __init__(
        self,
        stream_id: str,
        writer: StreamFileWriter,
        start_ts: float,
        last_seen_ts: float,
    ):
        self.stream_id = stream_id
        self.writer = writer
        self.start_ts = start_ts
        self.last_seen_ts = last_seen_ts
        self.packet_count = 0
        self.features_extracted = False


class PacketStreamDivider:
    def __init__(
        self,
        packet_csv: Path,
        output_dir: Path,
        extract_features: bool,
        prediction_queue: PredictionQueue,
        idle_timeout_sec: float = 30.0,
        max_packets: int = 100,
        max_duration_sec: float = 20.0,
    ):
        self.packet_csv = packet_csv
        self.output_dir = output_dir
        self.extract_features = extract_features
        self.prediction_queue = prediction_queue

        self.idle_timeout_sec = idle_timeout_sec
        self.max_packets = max_packets
        self.max_duration_sec = max_duration_sec

        self.active_streams: Dict[FlowKey, ActiveStream] = {}
        self.stream_counter = 0

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.extractor = StreamFeatureExtractor(idle_threshold=1.0)

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
            ts = float(value)
            return ts if ts > 0 else None
        except Exception:
            return None

    def _new_stream_id(self) -> str:
        self.stream_counter += 1
        return f"stream_{self.stream_counter:06d}"

    def _should_split(self, stream: ActiveStream, ts: float) -> bool:
        if (ts - stream.last_seen_ts) > self.idle_timeout_sec:
            return True
        if stream.packet_count >= self.max_packets:
            return True
        if (ts - stream.start_ts) >= self.max_duration_sec:
            return True
        return False

    def _finalize_stream(self, stream: ActiveStream) -> None:
        stream.writer.close()

        if self.extract_features and not stream.features_extracted:
            stats_saved = self.extractor.extract(stream.writer.path, stream.stream_id)
            if stats_saved:
                stream.features_extracted = True
                self.prediction_queue.enqueue(stream.stream_id)

    def _get_or_create_stream(
        self,
        key: FlowKey,
        header: list[str],
        ts: float,
        batch_id: str
    ) -> ActiveStream:
        existing = self.active_streams.get(key)

        if existing:
            if self._should_split(existing, ts):
                self._finalize_stream(existing)
                del self.active_streams[key]
            else:
                return existing

        new_stream_id = self._new_stream_id()
        stream_id = f"{batch_id}_{new_stream_id}"
        writer = StreamFileWriter(stream_id, self.output_dir, header)
        stream = ActiveStream(stream_id, writer, ts, ts)
        self.active_streams[key] = stream
        return stream

    def run(self, stop_event, batch_id) -> bool | None:
        with self.packet_csv.open("r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return

            for row in reader:
                record = dict(zip(header, row))
                ts = self._parse_epoch_timestamp(record.get("timestamp"))
                if ts is None:
                    continue

                key = self.canonical_flow_key(
                    record["src_ip"],
                    record["src_port"],
                    record["dst_ip"],
                    record["dst_port"],
                    record["transport"],
                )

                stream = self._get_or_create_stream(key, header, ts, batch_id)
                stream.writer.append(row)
                stream.packet_count += 1
                stream.last_seen_ts = ts

        # finalize remaining streams
        for stream in list(self.active_streams.values()):
            self._finalize_stream(stream)
        self.active_streams.clear()
