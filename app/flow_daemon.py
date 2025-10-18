#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import re
import time
import threading
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple, Optional, List, Mapping

import math

# ---- DB hooks (must exist in your project) ----
from app.database.db import session_scope
from app.database.crud import insert_flow_min, upsert_flow_stats

# -------------------- logging --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("FlowDaemon")

# -------------------- config --------------------
CONFIG = {
    "csv_path": r"D:\FYP_DEV\AIMchat2.csv",
    "poll_interval_sec": 2.0,
    "idle_timeout_sec": 15.0,      # also used to define 'active' windows for stats
    "active_timeout_sec": 1800.0,  # 30m
    "https_only": False,
    "protocol_filter": ["TCP", "UDP"],
    "output_dir": "app/data/extracted_pool",
    "columns": {
        "timestamp": "timestamp",
        "src_ip": "src_ip",
        "src_port": "src_port",
        "dst_ip": "dst_ip",
        "dst_port": "dst_port",
        "protocol": "protocol",
        "length": "length",        # optional; numeric bytes per packet if present
    },
    "max_threads": 5,              # thread pool bound for add_packet tasks
    "enable_stats": True,          # compute & store the 17 features into flow_stats
}

FiveKey = Tuple[str, str, str, str, str]  # (sip, sport, dip, dport, PROTO)


# -------------------------------------------------------------------------
# Data structures
# -------------------------------------------------------------------------
@dataclass
class ActiveFlow:
    flow_id: str
    key: FiveKey
    start_ts: float
    last_seen_ts: float
    packet_count: int
    csv_rel_path: Path
    # buffered (seq_no, ts, length)
    packet_times: List[Tuple[int, float, Optional[int]]] = field(default_factory=list)


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------
def canonical_key(sip: str, sport: str, dip: str, dport: str, proto: str) -> FiveKey:
    """
    Direction-agnostic 5-tuple so forward/reverse map to the same flow.
    """
    proto = proto.upper()
    a, b = (sip, sport), (dip, dport)
    low, high = (a, b) if a <= b else (b, a)
    return (low[0], low[1], high[0], high[1], proto)


def make_flow_id(key: FiveKey, start_ts: float) -> str:
    sip, sport, dip, dport, proto = key
    fid = f"{proto}-{sip}_{sport}--{dip}_{dport}__{int(start_ts * 1000)}"
    # file-system safe
    return re.sub(r'[<>:"/\\|?*]', "_", fid)


def _safe_int(v) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


# -------------------------------------------------------------------------
# Core tracker
# -------------------------------------------------------------------------
class FlowTracker:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.cols = cfg["columns"]
        self.out_dir = Path(cfg["output_dir"])
        (self.out_dir / "open").mkdir(parents=True, exist_ok=True)
        (self.out_dir / "final").mkdir(parents=True, exist_ok=True)

        self.active: Dict[FiveKey, ActiveFlow] = {}
        self._state_lock = threading.RLock()
        self._file_locks: Dict[Path, threading.Lock] = defaultdict(threading.Lock)

        self.stats = dict(packets_total=0, flows_started=0, flows_finalized=0, rows_skipped=0)

    # ---------- parsing & filters ----------
    @staticmethod
    def _parse_ts(raw: str) -> Optional[float]:
        """
        Parse timestamp robustly:
        - numeric (seconds)
        - ISO-8601 (with/without Z) -> seconds
        - pandas fallback
        """
        from datetime import datetime
        try:
            return float(raw)
        except Exception:
            pass
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except Exception:
            pass
        try:
            import pandas as pd
            val = pd.to_datetime(raw, errors="coerce", utc=True).value  # ns
            return float(val) / 1e9 if val == val else None
        except Exception:
            return None

    def _filter_packet(self, proto: str, sport: str, dport: str) -> bool:
        allowed = [p.upper() for p in self.cfg["protocol_filter"]]
        if proto.upper() not in allowed:
            return False
        if self.cfg["https_only"] and sport != "443" and dport != "443":
            return False
        return True

    # ---------- main entry ----------
    def add_packet(self, row: dict):
        ts = self._parse_ts(str(row.get(self.cols["timestamp"], "")))
        if ts is None:
            self.stats["rows_skipped"] += 1
            log.warning(f"[SKIP] Invalid timestamp row: {row}")
            return

        sip, dip = str(row.get(self.cols["src_ip"], "")), str(row.get(self.cols["dst_ip"], ""))
        sport, dport = str(row.get(self.cols["src_port"], "")), str(row.get(self.cols["dst_port"], ""))
        proto = str(row.get(self.cols["protocol"], "")).upper().strip()
        length_val = _safe_int(row.get(self.cols.get("length", ""), None))

        if not self._filter_packet(proto, sport, dport):
            return

        key = canonical_key(sip, sport, dip, dport, proto)
        now_ts = ts
        self.stats["packets_total"] += 1

        with self._state_lock:
            af = self.active.get(key)

            if af is None:
                self._create_new_flow(key, row, now_ts, length_val)
                return

            idle = float(self.cfg["idle_timeout_sec"])
            active_to = float(self.cfg.get("active_timeout_sec") or 0)

            if (now_ts - af.last_seen_ts) > idle or (active_to and (now_ts - af.start_ts) > active_to):
                self._finalize(af)  # move CSV + write DBs
                self._create_new_flow(key, row, now_ts, length_val)
            else:
                self._append_to_flow(af, row, now_ts, length_val)

    # ---------- file & state ops ----------
    def _create_new_flow(self, key: FiveKey, row: dict, ts: float, length_val: Optional[int]):
        fid = make_flow_id(key, ts)
        rel = Path("open") / f"{fid}.csv"
        abs_path = self.out_dir / rel

        with self._file_locks[abs_path]:
            is_new = not abs_path.exists()
            with abs_path.open("a", newline="") as f:
                w = csv.writer(f)
                if is_new:
                    w.writerow(self.cols.values())
                w.writerow([row.get(self.cols[k], "") for k in self.cols.keys()])

        af = ActiveFlow(
            flow_id=fid,
            key=key,
            start_ts=ts,
            last_seen_ts=ts,
            packet_count=1,
            csv_rel_path=rel,
            packet_times=[(1, ts, length_val)],
        )
        self.active[key] = af
        self.stats["flows_started"] += 1
        log.info(f"[NEW FLOW] {fid}")

    def _append_to_flow(self, af: ActiveFlow, row: dict, ts: float, length_val: Optional[int]):
        abs_path = self.out_dir / af.csv_rel_path
        with self._file_locks[abs_path]:
            with abs_path.open("a", newline="") as f:
                w = csv.writer(f)
                w.writerow([row.get(self.cols[k], "") for k in self.cols.keys()])

        af.packet_count += 1
        af.last_seen_ts = ts
        af.packet_times.append((af.packet_count, ts, length_val))
        log.debug(f"[APPEND] {af.flow_id} packet #{af.packet_count}")

    from app.database.models import FlowMin, FlowStats  # 🔁 replace crud import

    def _finalize(self, af: ActiveFlow):
        """
        On finalize:
          1) Move CSV open→final
          2) Insert minimal record into flows_min
          3) (Optional) compute & write 17 stats into flow_stats
        """
        src = self.out_dir / af.csv_rel_path
        dst = self.out_dir / "final" / src.name
        with self._file_locks[src]:
            for attempt in range(3):
                try:
                    os.replace(src, dst)
                    break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(0.2)
                    else:
                        log.warning(f"[WARN] Could not move {af.flow_id}: {e}")

        # 2) insert minimal FlowMin
        try:
            from app.database.models import FlowMin, FlowStats
            with session_scope() as db:
                if db.get(FlowMin, af.flow_id) is None:
                    FlowMin(flow_id=af.flow_id).save(db)
        except Exception as e:
            log.error(f"[DB] FlowMin save failed for {af.flow_id}: {e}")

        # 3) stats -> FlowStats
        if self.cfg.get("enable_stats", True):
            try:
                stats = compute_17_stats_from_csv(dst, self.cols, idle_threshold=float(self.cfg["idle_timeout_sec"]))
                if stats:
                    with session_scope() as db:
                        obj = db.get(FlowStats, af.flow_id)
                        if obj:
                            for k, v in stats.items():
                                setattr(obj, k, v)
                        else:
                            obj = FlowStats(flow_id=af.flow_id, **stats)
                        obj.save(db)
            except Exception as e:
                log.error(f"[DB] FlowStats save failed for {af.flow_id}: {e}")

        self.stats["flows_finalized"] += 1
        log.info(f"[SAVE] Flow {af.flow_id} → {dst}")

    def flush_timeouts(self, now_ts: float):
        idle = float(self.cfg["idle_timeout_sec"])
        with self._state_lock:
            expired = [k for k, af in self.active.items() if (now_ts - af.last_seen_ts) > idle]
            for key in expired:
                af = self.active[key]
                self._finalize(af)
                del self.active[key]
                log.info(f"[FLUSH] {af.flow_id} idle={now_ts - af.last_seen_ts:.2f}s")


# -------------------------------------------------------------------------
# Stats computation (the 17 features)
# -------------------------------------------------------------------------
from pathlib import Path
from typing import Mapping, Optional, List, Tuple
import pandas as pd
import numpy as np
import ipaddress

def _ts_to_seconds(series: pd.Series) -> pd.Series:
    """Robust numeric/datetime → float seconds (auto-detect s/ms/ns)."""
    ts_num = pd.to_numeric(series, errors="coerce")
    if ts_num.notna().mean() >= 0.9:
        med = np.nanmedian(ts_num)
        # Heuristics similar to your earlier script
        if med > 1e11:      # very large → likely nanoseconds
            return (ts_num / 1e9).astype(float)
        elif med > 1e10:    # borderline large → also nanoseconds
            return (ts_num / 1e9).astype(float)
        elif med > 1e6:     # likely milliseconds (Unix ms ~ 1.7e12; but some logs put ms as ~1e9)
            return (ts_num / 1e3).astype(float)
        else:               # seconds
            return ts_num.astype(float)
    # Datetime strings
    ts = pd.to_datetime(series, errors="coerce", utc=True)
    return ts.astype("int64") / 1e9  # ns → s


def _endpoint_key(ip_str: str, port_str: str) -> Tuple[Tuple[int, ...], int, str]:
    """Parse endpoint to a sortable key: (ip_octets_or_hextets, port_int, original_ip).
       Works for IPv4/IPv6; falls back to string if parsing fails."""
    try:
        ip = ipaddress.ip_address(ip_str)
        # For IPv4 → 4 octets; IPv6 → 16 bytes; both comparable as tuples
        ip_tuple = tuple(int(b) for b in ip.packed)
    except Exception:
        # fall back to string ordering if unparseable
        ip_tuple = tuple(map(ord, ip_str))
    try:
        p = int(port_str)
    except Exception:
        p = 0
    return (ip_tuple, p, ip_str)

def _stable_fwd_mask(df: pd.DataFrame, cols: Mapping[str, str]) -> pd.Series:
    """Decide a single 'forward' endpoint for the whole flow, then mark rows."""
    sip = df[cols["src_ip"]].astype(str)
    dip = df[cols["dst_ip"]].astype(str)
    sport = df[cols["src_port"]].astype(str)
    dport = df[cols["dst_port"]].astype(str)

    # Compute the canonical low/high endpoints ONCE using the first packet
    a_key = _endpoint_key(sip.iloc[0], sport.iloc[0])
    b_key = _endpoint_key(dip.iloc[0], dport.iloc[0])
    low_is_src = (a_key <= b_key)

    # Forward means "same side as the chosen low endpoint" across ALL packets
    if low_is_src:
        return (sip == sip.iloc[0]) & (sport == sport.iloc[0])
    else:
        return (sip == dip.iloc[0]) & (sport == dport.iloc[0])

def compute_17_stats_from_csv(path: Path, cols: Mapping[str, str], idle_threshold: float) -> Optional[dict]:
    """
    Compute 17 per-flow features compatible with your CNN/RL pipeline.

    Returns a dict with:
      duration, flowBytesPerSecond, flowPktsPerSecond,
      max_active, max_biat, max_fiat, max_flowiat,
      mean_biat, mean_fiat, mean_flowiat,
      min_biat, min_fiat, min_flowiat,
      std_active, std_flowiat,
      total_biat, total_fiat
    """
    try:
        df = pd.read_csv(path)
        if df.empty:
            return None

        # --- timestamps → seconds, then time-sort
        t_seconds = _ts_to_seconds(df[cols["timestamp"]])
        df = df.assign(__ts=t_seconds).sort_values("__ts").reset_index(drop=True)
        t = df["__ts"].astype(float)

        # --- lengths (optional → use 0 default)
        length_s = pd.to_numeric(df.get(cols.get("length", ""), pd.Series([0]*len(df))), errors="coerce").fillna(0.0)
        bytes_total = float(length_s.sum())

        # --- forward/backward (stable across flow)
        fwd_mask = _stable_fwd_mask(df, cols)
        tf = t[fwd_mask].reset_index(drop=True)
        tb = t[~fwd_mask].reset_index(drop=True)

        # --- Base
        n = len(t)
        if n <= 1:
            duration = 0.0
        else:
            duration = float(t.iloc[-1] - t.iloc[0])

        # Rates (sec-based)
        flowBytesPerSecond = (bytes_total / duration) if duration > 0 else 0.0
        flowPktsPerSecond  = (n / duration) if duration > 0 else 0.0

        # IATs
        iat = t.diff().dropna()
        def _stats(series: pd.Series):
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

        # Active windows: sum of consecutive gaps ≤ idle_threshold (seconds)
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
        # use your existing logger if available
        print(f"[STATS] Failed to compute stats from {path}: {e}")
        return None


# -------------------------------------------------------------------------
# Tail loop
# -------------------------------------------------------------------------
def tail_loop(cfg: dict, stop_event: Optional[threading.Event] = None):
    csv_path = Path(cfg["csv_path"]).resolve()
    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    tracker = FlowTracker(cfg)

    last_off = 0
    header_cache = None
    log.info(f"[INIT] Watching {csv_path}")

    with ThreadPoolExecutor(max_workers=cfg["max_threads"]) as executor:
        futures = []

        try:
            while True:
                if stop_event and stop_event.is_set():
                    log.info("[TAIL] Stop signal received — shutting down.")
                    break

                if not csv_path.exists():
                    log.info("[WAIT] CSV not found, retrying...")
                    time.sleep(cfg["poll_interval_sec"])
                    continue

                stat = csv_path.stat()
                if stat.st_size < last_off:
                    log.warning("[RESET] File truncated/rotated — restarting from 0.")
                    last_off, header_cache = 0, None

                with csv_path.open("r", newline="") as f:
                    if last_off == 0:
                        header_cache = next(csv.reader(f), None)
                        if header_cache is None:
                            time.sleep(cfg["poll_interval_sec"])
                            continue
                        missing = [col for col in cfg["columns"].values() if col not in header_cache]
                        if missing:
                            log.warning(f"[WARN] Missing expected columns: {missing}")

                    f.seek(last_off)
                    reader = csv.DictReader(f, fieldnames=header_cache if last_off > 0 else None)

                    for row in reader:
                        if row.get("timestamp") == "timestamp":
                            continue
                        futures.append(executor.submit(tracker.add_packet, row))
                    last_off = f.tell()

                tracker.flush_timeouts(time.time())
                futures = [ft for ft in futures if not ft.done()]

                log.info(f"[POOL] active_tasks={len(futures)} open_flows={len(tracker.active)} last_off={last_off}")
                time.sleep(cfg["poll_interval_sec"])

        except Exception as e:
            log.exception(f"[ERROR] Unexpected exception in tail loop: {e}")

        finally:
            log.info("[TAIL] Final flush before shutdown...")
            tracker.flush_timeouts(time.time())
            log.info(f"[TAIL] Final stats: {tracker.stats}")


# -------------------------------------------------------------------------
# Entry (standalone)
# -------------------------------------------------------------------------
if __name__ == "__main__":
    Path(CONFIG["output_dir"]).mkdir(parents=True, exist_ok=True)
    tail_loop(CONFIG)
