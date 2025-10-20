from __future__ import annotations

from pathlib import Path
from typing import Mapping, Optional, List

import pandas as pd

from app.network_flow_tracker.helpers import _ts_to_seconds, _stable_fwd_mask


def compute_17_stats_from_csv(path: Path, cols: Mapping[str, str], idle_threshold: float) -> Optional[dict]:
    """Computes core 17 flow statistics from a CSV file."""
    try:
        df = pd.read_csv(path)
        if df.empty:
            return None
        t_seconds = _ts_to_seconds(df[cols["timestamp"]])
        df = df.assign(__ts=t_seconds).sort_values("__ts").reset_index(drop=True)
        t = df["__ts"].astype(float)
        length_s = pd.to_numeric(df.get(cols.get("length", ""), pd.Series([0] * len(df))), errors="coerce").fillna(0.0)
        bytes_total = float(length_s.sum())
        fwd_mask = _stable_fwd_mask(df, cols)
        tf = t[fwd_mask].reset_index(drop=True)
        tb = t[~fwd_mask].reset_index(drop=True)
        n = len(t)
        duration = 0.0 if n <= 1 else float(t.iloc[-1] - t.iloc[0])
        flowBytesPerSecond = (bytes_total / duration) if duration > 0 else 0.0
        flowPktsPerSecond = (n / duration) if duration > 0 else 0.0
        iat = t.diff().dropna()

        def _stats(series: pd.Series):
            """Aggregates max/mean/min/std/total for a series."""
            if series is None or series.empty:
                return dict(max=0.0, mean=0.0, min=0.0, std=0.0, total=0.0)
            return dict(
                max=float(series.max()),
                mean=float(series.mean()),
                min=float(series.min()),
                std=float(series.std(ddof=1)) if len(series) > 1 else 0.0,
                total=float(series.sum()),
            )

        flow_s = _stats(iat)
        fiat = tf.diff().dropna()
        biat = tb.diff().dropna()
        f_s = _stats(fiat)
        b_s = _stats(biat)
        max_active = 0.0
        std_active = 0.0
        if not iat.empty:
            spans: List[float] = []
            acc = 0.0
            for gap in iat:
                if gap <= idle_threshold:
                    acc += float(gap)
                else:
                    spans.append(acc)
                    acc = 0.0
            spans.append(acc)
            if spans:
                max_active = max(spans)
                std_active = float(pd.Series(spans).std(ddof=1)) if len(spans) > 1 else 0.0
        return {
            "duration": duration,
            "flowBytesPerSecond": flowBytesPerSecond,
            "flowPktsPerSecond": flowPktsPerSecond,
            "max_active": max_active,
            "max_biat": b_s["max"],
            "max_fiat": f_s["max"],
            "max_flowiat": flow_s["max"],
            "mean_biat": b_s["mean"],
            "mean_fiat": f_s["mean"],
            "mean_flowiat": flow_s["mean"],
            "min_biat": b_s["min"],
            "min_fiat": f_s["min"],
            "min_flowiat": flow_s["min"],
            "std_active": std_active,
            "std_flowiat": flow_s["std"],
            "total_biat": b_s["total"],
            "total_fiat": f_s["total"],
        }
    except Exception as e:
        print(f"[STATS] Failed to compute stats from {path}: {e}")
        return None
