from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Any

import pandas as pd

from app.database.db import session_scope
from app.database.models import FlowStats


class StreamFeatureExtractor:
    def __init__(self, idle_threshold: float = 1.0):
        self.idle_threshold = idle_threshold

    def extract(
        self,
        stream_csv: Path,
        flow_id: str,
    ) -> bool | None:
        df = pd.read_csv(stream_csv)

        if df.empty or len(df) < 1:
            return None

        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
        df["packet_length"] = pd.to_numeric(df["packet_length"], errors="coerce").fillna(0.0)
        df = (
            df.dropna(subset=["timestamp"])
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        if len(df) < 2:
            return None

        timestamps = df["timestamp"]
        lengths = df["packet_length"]

        start_time = float(timestamps.iloc[0])
        end_time = float(timestamps.iloc[-1])
        duration = end_time - start_time

        if duration <= 0:
            return None

        total_bytes = float(lengths.sum())
        total_packets = len(df)

        flowBytesPerSecond = total_bytes / duration
        flowPktsPerSecond = total_packets / duration

        flow_iat = timestamps.diff().dropna()
        flow_s = self._stats(flow_iat)

        forward_mask = self._forward_mask(df)

        tf = timestamps[forward_mask].reset_index(drop=True)
        tb = timestamps[~forward_mask].reset_index(drop=True)

        fiat = tf.diff().dropna()
        biat = tb.diff().dropna()

        f_s = self._stats(fiat)
        b_s = self._stats(biat)

        max_active, std_active = self._active_stats(flow_iat)

        flow_stats = FlowStats(
            flow_id=flow_id,
            start_time=float(start_time),
            end_time=float(end_time),
            duration=duration,
            flowBytesPerSecond=flowBytesPerSecond,
            flowPktsPerSecond=flowPktsPerSecond,
            max_active=max_active,
            std_active=std_active,
            max_biat=b_s["max"],
            mean_biat=b_s["mean"],
            min_biat=b_s["min"],
            total_biat=b_s["total"],
            max_fiat=f_s["max"],
            mean_fiat=f_s["mean"],
            min_fiat=f_s["min"],
            total_fiat=f_s["total"],
            max_flowiat=flow_s["max"],
            mean_flowiat=flow_s["mean"],
            min_flowiat=flow_s["min"],
            std_flowiat=flow_s["std"],
        )
        with session_scope() as db:
            flow_stats.save(db)

        return True

    @staticmethod
    def _stats(series: pd.Series) -> Dict[str, float]:
        if series.empty:
            return {"max": 0.0, "mean": 0.0, "min": 0.0, "std": 0.0, "total": 0.0}

        return {
            "max": float(series.max()),
            "mean": float(series.mean()),
            "min": float(series.min()),
            "std": float(series.std(ddof=1)) if len(series) > 1 else 0.0,
            "total": float(series.sum()),
        }

    @staticmethod
    def _forward_mask(df: pd.DataFrame) -> bool:
        first_src = df.loc[0, "src_ip"]
        first_sport = df.loc[0, "src_port"]
        return (df["src_ip"] == first_src) & (df["src_port"] == first_sport)

    def _active_stats(self, flow_iat: pd.Series) -> tuple[float, float]:
        if flow_iat.empty:
            return 0.0, 0.0

        active_periods: list[float] = []
        acc = 0.0

        for gap in flow_iat:
            gap = float(gap)
            if gap <= self.idle_threshold:
                acc += gap
            else:
                if acc > 0.0:
                    active_periods.append(acc)
                    acc = 0.0

        if acc > 0.0:
            active_periods.append(acc)

        if not active_periods:
            return 0.0, 0.0

        s = pd.Series(active_periods, dtype="float64")
        return float(s.max()), float(s.std(ddof=0))
