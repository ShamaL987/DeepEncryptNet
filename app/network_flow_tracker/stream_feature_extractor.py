from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app.database.db import session_scope
from app.database.models import ISCXFlowStatsV2, FlowRegistry, ISCXFlowStatsV1, HTTPSFlowStats


@dataclass
class Burst:
    direction: str
    start_time: float
    end_time: float
    packet_count: int
    byte_count: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)


class BasePacketStreamFeatureExtractor:
    def __init__(self, idle_threshold: float = 1.0):
        self.idle_threshold = idle_threshold

    def extract(self, stream_csv: Path, flow_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @staticmethod
    def _stats(series: pd.Series) -> dict[str, float]:
        if series.empty:
            return {
                "max": 0.0,
                "mean": 0.0,
                "min": 0.0,
                "std": 0.0,
                "total": 0.0,
            }

        return {
            "max": float(series.max()),
            "mean": float(series.mean()),
            "min": float(series.min()),
            "std": float(series.std(ddof=1)) if len(series) > 1 else 0.0,
            "total": float(series.sum()),
        }

    @staticmethod
    def _quantile(series: pd.Series, q: float) -> float:
        if series.empty:
            return 0.0
        return float(series.quantile(q))

    @staticmethod
    def _forward_mask(df: pd.DataFrame) -> pd.Series:
        first_src = str(df.loc[0, "src_ip"])
        first_sport = str(df.loc[0, "src_port"])
        return (df["src_ip"].astype(str) == first_src) & (df["src_port"].astype(str) == first_sport)

    def _load_stream_df(self, stream_csv: Path) -> pd.DataFrame | None:
        df = pd.read_csv(stream_csv)

        if df.empty:
            return None

        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
        df["packet_length"] = pd.to_numeric(df["packet_length"], errors="coerce").fillna(0.0)

        if "frame_number" in df.columns:
            df["frame_number"] = pd.to_numeric(df["frame_number"], errors="coerce")
        else:
            df["frame_number"] = range(1, len(df) + 1)

        required_columns = ["timestamp", "frame_number", "src_ip", "src_port", "dst_ip", "dst_port", "packet_length"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required stream CSV columns: {missing_columns}")

        df = (
            df.dropna(subset=["timestamp", "frame_number"])
            .sort_values(["timestamp", "frame_number"])
            .reset_index(drop=True)
        )

        if df.empty:
            return None

        return df

    def _active_stats(self, flow_iat: pd.Series) -> tuple[float, float]:
        if flow_iat.empty:
            return 0.0, 0.0

        active_periods: list[float] = []
        accumulated = 0.0

        for gap in flow_iat:
            gap_value = float(gap)
            if gap_value <= self.idle_threshold:
                accumulated += gap_value
            else:
                if accumulated > 0.0:
                    active_periods.append(accumulated)
                    accumulated = 0.0

        if accumulated > 0.0:
            active_periods.append(accumulated)

        if not active_periods:
            return 0.0, 0.0

        active_series = pd.Series(active_periods, dtype="float64")
        return float(active_series.max()), float(active_series.std(ddof=0))


from pathlib import Path
from typing import Any

import pandas as pd


class HTTPSStreamFeatureExtractor(BasePacketStreamFeatureExtractor):
    def __init__(self, burst_gap_threshold: float = 1.0):
        super().__init__(idle_threshold=burst_gap_threshold)
        self.burst_gap_threshold = burst_gap_threshold

    @staticmethod
    def _safe_div(numerator: float, denominator: float) -> float:
        denominator_value = float(denominator)
        if abs(denominator_value) < 1e-12:
            return 0.0
        return float(numerator) / denominator_value

    def _coefficient_of_variation(self, values: pd.Series) -> float:
        if values.empty:
            return 0.0
        mean_value = float(values.mean())
        std_value = float(values.std(ddof=1)) if len(values) > 1 else 0.0
        return self._safe_div(std_value, mean_value)

    def _iqr_ratio(self, values: pd.Series) -> float:
        if values.empty:
            return 0.0
        q25 = self._quantile(values, 0.25)
        q50 = self._quantile(values, 0.50)
        q75 = self._quantile(values, 0.75)
        return self._safe_div(q75 - q25, q50)

    @staticmethod
    def _direction_switch_rate(direction_mask: pd.Series) -> float:
        if len(direction_mask) < 2:
            return 0.0
        direction_values = direction_mask.astype(int).reset_index(drop=True)
        switches = direction_values.ne(direction_values.shift(1)).iloc[1:]
        return float(switches.mean()) if not switches.empty else 0.0

    def extract(self, stream_csv: Path, flow_id: str) -> dict[str, Any] | None:
        df = self._load_stream_df(stream_csv)
        if df is None or df.empty:
            return None

        df = df.reset_index(drop=True)
        forward_mask = self._forward_mask(df).reset_index(drop=True)

        timestamps = df["timestamp"].astype(float).reset_index(drop=True)
        lengths = df["packet_length"].astype(float).reset_index(drop=True)

        forward_lengths = lengths[forward_mask].reset_index(drop=True)
        reverse_lengths = lengths[~forward_mask].reset_index(drop=True)

        intervals = timestamps.diff().dropna().reset_index(drop=True)
        bursts = self._build_bursts(df, forward_mask)

        burst_bytes = pd.Series([float(burst.byte_count) for burst in bursts], dtype="float64")
        burst_packets = pd.Series([float(burst.packet_count) for burst in bursts], dtype="float64")
        burst_durations = pd.Series([float(burst.duration) for burst in bursts], dtype="float64")
        burst_intervals = pd.Series(self._build_burst_intervals(bursts), dtype="float64")

        total_packets = int(len(lengths))
        total_bytes = float(lengths.sum())
        forward_packets = int(forward_mask.sum())
        forward_bytes = float(forward_lengths.sum())

        prefix_duration = float(timestamps.iloc[-1] - timestamps.iloc[0]) if len(timestamps) > 1 else 0.0
        prefix_direction_switch_rate = self._direction_switch_rate(forward_mask)

        prefix_mean_fwd_len = float(forward_lengths.mean()) if not forward_lengths.empty else 0.0
        prefix_mean_rev_len = float(reverse_lengths.mean()) if not reverse_lengths.empty else 0.0

        pkt_lengths_mean = float(lengths.mean()) if not lengths.empty else 0.0
        pkt_lengths_max = float(lengths.max()) if not lengths.empty else 0.0
        pkt_lengths_std = float(lengths.std(ddof=1)) if len(lengths) > 1 else 0.0
        pkt_lengths_25 = self._quantile(lengths, 0.25)
        pkt_lengths_50 = self._quantile(lengths, 0.50)
        pkt_lengths_75 = self._quantile(lengths, 0.75)

        intervals_mean = float(intervals.mean()) if not intervals.empty else 0.0
        intervals_max = float(intervals.max()) if not intervals.empty else 0.0
        intervals_std = float(intervals.std(ddof=1)) if len(intervals) > 1 else 0.0
        intervals_25 = self._quantile(intervals, 0.25)
        intervals_50 = self._quantile(intervals, 0.50)
        intervals_75 = self._quantile(intervals, 0.75)

        burst_bytes_per_packet = (
            burst_bytes.divide(burst_packets.where(burst_packets != 0, other=pd.NA))
            .fillna(0.0)
            .astype(float)
        ) if not burst_bytes.empty else pd.Series(dtype="float64")

        brst_intervals_mean = float(burst_intervals.mean()) if not burst_intervals.empty else 0.0
        brst_intervals_max = float(burst_intervals.max()) if not burst_intervals.empty else 0.0
        brst_intervals_std = float(burst_intervals.std(ddof=1)) if len(burst_intervals) > 1 else 0.0
        brst_intervals_25 = self._quantile(burst_intervals, 0.25)

        brst_duration_mean = float(burst_durations.mean()) if not burst_durations.empty else 0.0
        brst_duration_max = float(burst_durations.max()) if not burst_durations.empty else 0.0
        brst_duration_std = float(burst_durations.std(ddof=1)) if len(burst_durations) > 1 else 0.0

        features: dict[str, Any] = {
            "flow_id": flow_id,
            "prefix_duration": prefix_duration,
            "prefix_bytes_per_second": self._safe_div(total_bytes, prefix_duration),
            "prefix_pkts_per_second": self._safe_div(total_packets, prefix_duration),
            "prefix_fwd_pkt_share": self._safe_div(forward_packets, total_packets),
            "prefix_fwd_byte_share": self._safe_div(forward_bytes, total_bytes),
            "prefix_dir_switch_rate": prefix_direction_switch_rate,
            "prefix_mean_fwd_len": prefix_mean_fwd_len,
            "prefix_mean_rev_len": prefix_mean_rev_len,
            "prefix_fwd_rev_mean_len_ratio": self._safe_div(prefix_mean_fwd_len, prefix_mean_rev_len),
            "pkt_len_cv": self._safe_div(pkt_lengths_std, pkt_lengths_mean),
            "pkt_len_iqr_ratio": self._safe_div(pkt_lengths_75 - pkt_lengths_25, pkt_lengths_50),
            "iat_cv": self._safe_div(intervals_std, intervals_mean),
            "iat_iqr_ratio": self._safe_div(intervals_75 - intervals_25, intervals_50),
            "burst_count_per_second": self._safe_div(len(bursts), prefix_duration),
            "burst_mean_bytes_per_packet": float(burst_bytes_per_packet.mean()) if not burst_bytes_per_packet.empty else 0.0,
            "burst_std_bytes_per_packet": float(burst_bytes_per_packet.std(ddof=1)) if len(burst_bytes_per_packet) > 1 else 0.0,
            "burst_top1_byte_share": self._safe_div(float(burst_bytes.max()) if not burst_bytes.empty else 0.0, float(burst_bytes.sum()) if not burst_bytes.empty else 0.0),
            "burst_interval_cv": self._coefficient_of_variation(burst_intervals),
            "burst_interval_iqr_ratio": self._iqr_ratio(burst_intervals),
            "burst_duration_cv": self._coefficient_of_variation(burst_durations),
            "burst_duration_iqr_ratio": self._iqr_ratio(burst_durations),
            "PKT_LENGTHS_MEAN": pkt_lengths_mean,
            "PKT_LENGTHS_MAX": pkt_lengths_max,
            "PKT_LENGTHS_STD": pkt_lengths_std,
            "PKT_LENGTHS_25": pkt_lengths_25,
            "PKT_LENGTHS_50": pkt_lengths_50,
            "PKT_LENGTHS_75": pkt_lengths_75,
            "INTERVALS_MEAN": intervals_mean,
            "INTERVALS_MAX": intervals_max,
            "INTERVALS_STD": intervals_std,
            "INTERVALS_25": intervals_25,
            "INTERVALS_50": intervals_50,
            "INTERVALS_75": intervals_75,
            "BRST_INTERVALS_MEAN": brst_intervals_mean,
            "BRST_INTERVALS_MAX": brst_intervals_max,
            "BRST_INTERVALS_STD": brst_intervals_std,
            "BRST_INTERVALS_25": brst_intervals_25,
            "BRST_DURATION_MEAN": brst_duration_mean,
            "BRST_DURATION_MAX": brst_duration_max,
            "BRST_DURATION_STD": brst_duration_std,
        }

        with session_scope() as db:
            flow_registry = FlowRegistry(
                flow_id=flow_id,
                pipeline_name="HTTPS",
            )
            flow_registry.save(db)

            stats_row = HTTPSFlowStats(**features)
            stats_row.save(db)

        return features

    def _build_bursts(self, df: pd.DataFrame, forward_mask: pd.Series) -> list[Burst]:
        bursts: list[Burst] = []
        current_burst: Burst | None = None

        timestamps = df["timestamp"].astype(float).reset_index(drop=True)
        lengths = df["packet_length"].astype(float).reset_index(drop=True)
        directions = forward_mask.reset_index(drop=True).map(lambda is_forward: "fwd" if is_forward else "rev")

        for index in range(len(df)):
            timestamp = float(timestamps.iloc[index])
            packet_length = float(lengths.iloc[index])
            direction = str(directions.iloc[index])

            if current_burst is None:
                current_burst = Burst(
                    direction=direction,
                    start_time=timestamp,
                    end_time=timestamp,
                    packet_count=1,
                    byte_count=packet_length,
                )
                continue

            gap = timestamp - current_burst.end_time
            should_start_new_burst = (
                direction != current_burst.direction
                or gap > self.burst_gap_threshold
            )

            if should_start_new_burst:
                bursts.append(current_burst)
                current_burst = Burst(
                    direction=direction,
                    start_time=timestamp,
                    end_time=timestamp,
                    packet_count=1,
                    byte_count=packet_length,
                )
                continue

            current_burst.end_time = timestamp
            current_burst.packet_count += 1
            current_burst.byte_count += packet_length

        if current_burst is not None:
            bursts.append(current_burst)

        return bursts

    @staticmethod
    def _build_burst_intervals(bursts: list[Burst]) -> list[float]:
        if len(bursts) < 2:
            return []

        intervals: list[float] = []
        for index in range(1, len(bursts)):
            gap = bursts[index].start_time - bursts[index - 1].end_time
            intervals.append(max(0.0, float(gap)))
        return intervals


class ISCXV1StreamFeatureExtractor(BasePacketStreamFeatureExtractor):
    def extract(self, stream_csv: Path, flow_id: str) -> dict[str, Any] | None:
        df = self._load_stream_df(stream_csv)
        if df is None or len(df) < 2:
            return None

        timestamps = df["timestamp"].astype(float).reset_index(drop=True)
        lengths = df["packet_length"].astype(float).reset_index(drop=True)

        start_time = float(timestamps.iloc[0])
        end_time = float(timestamps.iloc[-1])
        duration = end_time - start_time

        if duration <= 0:
            return None

        total_bytes = float(lengths.sum())
        total_packets = len(df)

        flow_bytes_per_second = total_bytes / duration
        flow_packets_per_second = total_packets / duration

        flow_iat = timestamps.diff().dropna().reset_index(drop=True)
        flow_stats = self._stats(flow_iat)

        forward_mask = self._forward_mask(df)

        forward_timestamps = timestamps[forward_mask].reset_index(drop=True)
        reverse_timestamps = timestamps[~forward_mask].reset_index(drop=True)

        forward_iat = forward_timestamps.diff().dropna().reset_index(drop=True)
        reverse_iat = reverse_timestamps.diff().dropna().reset_index(drop=True)

        forward_stats = self._stats(forward_iat)
        reverse_stats = self._stats(reverse_iat)

        max_active, std_active = self._active_stats(flow_iat)

        with session_scope() as db:
            flow_registry = FlowRegistry(
                flow_id=flow_id,
                pipeline_name="ISCX_V1",
            )
            flow_registry.save(db)

            stats_row = ISCXFlowStatsV1(
                flow_id=flow_id,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                flowBytesPerSecond=flow_bytes_per_second,
                flowPktsPerSecond=flow_packets_per_second,
                max_active=max_active,
                std_active=std_active,
                max_biat=reverse_stats["max"],
                mean_biat=reverse_stats["mean"],
                min_biat=reverse_stats["min"],
                total_biat=reverse_stats["total"],
                max_fiat=forward_stats["max"],
                mean_fiat=forward_stats["mean"],
                min_fiat=forward_stats["min"],
                total_fiat=forward_stats["total"],
                max_flowiat=flow_stats["max"],
                mean_flowiat=flow_stats["mean"],
                min_flowiat=flow_stats["min"],
                std_flowiat=flow_stats["std"],
            )
            stats_row.save(db)

        return {
            "flow_id": flow_id,
            "duration": float(duration),
            "flowBytesPerSecond": float(flow_bytes_per_second),
            "flowPktsPerSecond": float(flow_packets_per_second),
            "max_active": float(max_active),
            "max_biat": float(reverse_stats["max"]),
            "max_fiat": float(forward_stats["max"]),
            "max_flowiat": float(flow_stats["max"]),
            "mean_biat": float(reverse_stats["mean"]),
            "mean_fiat": float(forward_stats["mean"]),
            "mean_flowiat": float(flow_stats["mean"]),
            "min_biat": float(reverse_stats["min"]),
            "min_fiat": float(forward_stats["min"]),
            "min_flowiat": float(flow_stats["min"]),
            "std_active": float(std_active),
            "std_flowiat": float(flow_stats["std"]),
            "total_biat": float(reverse_stats["total"]),
            "total_fiat": float(forward_stats["total"]),
        }


class ISCXV2StreamFeatureExtractor(BasePacketStreamFeatureExtractor):
    def extract(self, stream_csv: Path, flow_id: str) -> dict[str, Any] | None:
        df = self._load_stream_df(stream_csv)
        if df is None or len(df) < 2:
            return None

        timestamps = df["timestamp"].astype(float).reset_index(drop=True)
        lengths = df["packet_length"].astype(float).reset_index(drop=True)

        start_time = float(timestamps.iloc[0])
        end_time = float(timestamps.iloc[-1])
        duration = end_time - start_time

        if duration <= 0:
            return None

        total_bytes = float(lengths.sum())
        total_packets = len(df)

        flow_bytes_per_second = total_bytes / duration
        flow_packets_per_second = total_packets / duration

        flow_iat = timestamps.diff().dropna().reset_index(drop=True)
        flow_stats = self._stats(flow_iat)

        forward_mask = self._forward_mask(df)

        forward_timestamps = timestamps[forward_mask].reset_index(drop=True)
        reverse_timestamps = timestamps[~forward_mask].reset_index(drop=True)

        forward_iat = forward_timestamps.diff().dropna().reset_index(drop=True)
        reverse_iat = reverse_timestamps.diff().dropna().reset_index(drop=True)

        forward_stats = self._stats(forward_iat)
        reverse_stats = self._stats(reverse_iat)

        max_active, std_active = self._active_stats(flow_iat)

        with session_scope() as db:
            flow_registry = FlowRegistry(
                flow_id=flow_id,
                pipeline_name="ISCX_V2",
            )
            flow_registry.save(db)

            stats_row = ISCXFlowStatsV2(
                flow_id=flow_id,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                flowBytesPerSecond=flow_bytes_per_second,
                flowPktsPerSecond=flow_packets_per_second,
                max_active=max_active,
                std_active=std_active,
                max_biat=reverse_stats["max"],
                mean_biat=reverse_stats["mean"],
                min_biat=reverse_stats["min"],
                total_biat=reverse_stats["total"],
                std_biat=reverse_stats["std"],
                max_fiat=forward_stats["max"],
                mean_fiat=forward_stats["mean"],
                min_fiat=forward_stats["min"],
                total_fiat=forward_stats["total"],
                std_fiat=forward_stats["std"],
                max_flowiat=flow_stats["max"],
                mean_flowiat=flow_stats["mean"],
                min_flowiat=flow_stats["min"],
                std_flowiat=flow_stats["std"],
            )
            stats_row.save(db)

        return {
            "flow_id": flow_id,
            "duration": float(duration),
            "flowBytesPerSecond": float(flow_bytes_per_second),
            "flowPktsPerSecond": float(flow_packets_per_second),
            "max_active": float(max_active),
            "max_biat": float(reverse_stats["max"]),
            "max_fiat": float(forward_stats["max"]),
            "mean_biat": float(reverse_stats["mean"]),
            "mean_fiat": float(forward_stats["mean"]),
            "mean_flowiat": float(flow_stats["mean"]),
            "min_biat": float(reverse_stats["min"]),
            "min_fiat": float(forward_stats["min"]),
            "min_flowiat": float(flow_stats["min"]),
            "std_active": float(std_active),
            "std_biat": float(reverse_stats["std"]),
            "std_fiat": float(forward_stats["std"]),
            "std_flowiat": float(flow_stats["std"]),
            "total_biat": float(reverse_stats["total"]),
            "total_fiat": float(forward_stats["total"]),
        }


class PipelineStreamFeatureExtractorFactory:
    @staticmethod
    def create(pipeline_name: str, idle_threshold: float = 1.0) -> BasePacketStreamFeatureExtractor:
        normalized_name = pipeline_name.strip().upper()

        if normalized_name == "HTTPS":
            return HTTPSStreamFeatureExtractor(burst_gap_threshold=idle_threshold)

        if normalized_name == "ISCX_V1":
            return ISCXV1StreamFeatureExtractor(idle_threshold=idle_threshold)

        if normalized_name == "ISCX_V2":
            return ISCXV2StreamFeatureExtractor(idle_threshold=idle_threshold)

        raise ValueError(
            f"Unsupported pipeline_name '{pipeline_name}'. "
            f"Supported values are: HTTPS, ISCX_V2"
        )


class ConfiguredPipelineStreamFeatureExtractor:
    def __init__(self, pipeline_name: str, idle_threshold: float = 1.0):
        self.pipeline_name = pipeline_name
        self.extractor = PipelineStreamFeatureExtractorFactory.create(
            pipeline_name=pipeline_name,
            idle_threshold=idle_threshold,
        )

    def extract(self, stream_csv: Path, flow_id: str) -> dict[str, Any] | None:
        return self.extractor.extract(stream_csv=stream_csv, flow_id=flow_id)