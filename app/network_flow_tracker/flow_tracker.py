from __future__ import annotations

import csv
import os
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from app.database.db import session_scope
from app.network_flow_tracker.feature_extraction import compute_17_stats_from_csv
from app.network_flow_tracker.helpers import FiveKey, ActiveFlow, canonical_key, make_flow_id, _safe_int
from app.settings import log


class FlowTracker:
    """Tracks open flows and writes rows to per-flow CSVs."""

    def __init__(self, cfg):
        """Initializes state and output directories."""
        self.cfg = cfg
        self.cols = cfg.get("columns")
        self.out_dir = Path(cfg.get("output_dir"))
        (self.out_dir / "open").mkdir(parents=True, exist_ok=True)
        (self.out_dir / "final").mkdir(parents=True, exist_ok=True)
        self.active: Dict[FiveKey, ActiveFlow] = {}
        self._state_lock = threading.RLock()
        self._file_locks: Dict[Path, threading.Lock] = defaultdict(threading.Lock)
        self.stats = dict(packets_total=0, flows_started=0, flows_finalized=0, rows_skipped=0)

    @staticmethod
    def _parse_ts(raw: str) -> Optional[float]:
        """Parses a timestamp into seconds since epoch."""
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
            val = pd.to_datetime(raw, errors="coerce", utc=True).value
            return float(val) / 1e9 if val == val else None
        except Exception:
            return None

    def _filter_packet(self, proto: str, sport: str, dport: str) -> bool:
        """Checks protocol and HTTPS-only filters."""
        allowed = [p.upper() for p in self.cfg.get("protocol_filter")]
        if proto.upper() not in allowed:
            return False
        if self.cfg.get("https_only") and sport != "443" and dport != "443":
            return False
        return True

    def add_packet(self, row: dict):
        """Adds a packet row into the appropriate flow."""
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
            idle = float(self.cfg.get("idle_timeout_sec"))
            active_to = float(self.cfg.get("active_timeout_sec") or 0)
            if (now_ts - af.last_seen_ts) > idle or (active_to and (now_ts - af.start_ts) > active_to):
                self._finalize(af)
                self._create_new_flow(key, row, now_ts, length_val)
            else:
                self._append_to_flow(af, row, now_ts, length_val)

    def _create_new_flow(self, key: FiveKey, row: dict, ts: float, length_val: Optional[int]):
        """Creates a new flow and writes the first row."""
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
        """Appends a packet row to an existing flow."""
        abs_path = self.out_dir / af.csv_rel_path
        with self._file_locks[abs_path]:
            with abs_path.open("a", newline="") as f:
                w = csv.writer(f)
                w.writerow([row.get(self.cols[k], "") for k in self.cols.keys()])
        af.packet_count += 1
        af.last_seen_ts = ts
        af.packet_times.append((af.packet_count, ts, length_val))
        log.debug(f"[APPEND] {af.flow_id} packet #{af.packet_count}")

    def _finalize(self, af: ActiveFlow):
        """Finalizes a flow, moves CSV, and writes stats to DB."""
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
        try:
            from app.database.models import FlowMin, FlowStats
            with session_scope() as db:
                if db.get(FlowMin, af.flow_id) is None:
                    FlowMin(flow_id=af.flow_id).save(db)
        except Exception as e:
            log.error(f"[DB] FlowMin save failed for {af.flow_id}: {e}")
        if self.cfg.get("enable_stats", True):
            try:
                stats = compute_17_stats_from_csv(dst, self.cols, idle_threshold=float(self.cfg.get("idle_timeout_sec")))
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
        """Finalizes flows that exceeded the idle timeout."""
        idle = float(self.cfg.get("idle_timeout_sec"))
        with self._state_lock:
            expired = [k for k, af in self.active.items() if (now_ts - af.last_seen_ts) > idle]
            for key in expired:
                af = self.active[key]
                self._finalize(af)
                del self.active[key]
                log.info(f"[FLUSH] {af.flow_id} idle={now_ts - af.last_seen_ts:.2f}s")
