#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import re
import time
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor

# ---------- CONFIG ----------
CONFIG = {
    "csv_path": r"D:\FYP_DEV\AIMchat2.csv",
    "poll_interval_sec": 2.0,
    "idle_timeout_sec": 15.0,
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
    },
    "max_threads": 5  # limit for thread pool
}
# -------------------------------------------------------------------------

FiveKey = Tuple[str, str, str, str, str]  # (sip, sport, dip, dport, PROTO)

@dataclass
class ActiveFlow:
    flow_id: str
    key: FiveKey
    start_ts: float
    last_seen_ts: float
    packet_count: int
    csv_rel_path: Path

def canonical_key(sip: str, sport: str, dip: str, dport: str, proto: str) -> FiveKey:
    proto = proto.upper()
    a = (sip, sport)
    b = (dip, dport)
    low, high = (a, b) if a <= b else (b, a)
    return (low[0], low[1], high[0], high[1], proto)

def make_flow_id(key: FiveKey, start_ts: float) -> str:
    sip, sport, dip, dport, proto = key
    fid = f"{proto}-{sip}_{sport}--{dip}_{dport}__{int(start_ts*1000)}"
    return re.sub(r'[<>:"/\\|?*]', '_', fid)

class FlowTracker:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.cols = cfg["columns"]
        self.out_dir = Path(cfg["output_dir"])
        (self.out_dir / "open").mkdir(parents=True, exist_ok=True)
        (self.out_dir / "final").mkdir(parents=True, exist_ok=True)
        self.active: Dict[FiveKey, ActiveFlow] = {}

        # synchronization
        self._state_lock = threading.RLock()  # protects self.active + finalize decisions
        self._file_locks: Dict[Path, threading.Lock] = defaultdict(threading.Lock)  # per-file locks

    # -------- helpers --------
    def _filter_packet(self, proto: str, sport: str, dport: str) -> bool:
        if self.cfg["protocol_filter"] and proto.upper() not in [p.upper() for p in self.cfg["protocol_filter"]]:
            return False
        if self.cfg["https_only"]:
            if sport != "443" and dport != "443":
                return False
        return True

    @staticmethod
    def _parse_ts(raw: str) -> Optional[float]:
        # try numeric
        try:
            return float(raw)
        except Exception:
            pass
        # try ISO-8601
        try:
            from datetime import datetime
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except Exception:
            pass
        # last resort via pandas (optional)
        try:
            import pandas as pd
            v = pd.to_datetime(raw, errors="coerce").value
            if v and v == v:  # not NaT
                return float(v) / 1e9
        except Exception:
            pass
        return None

    # -------- main API --------
    def add_packet(self, row: dict):
        ts = self._parse_ts(str(row.get(self.cols["timestamp"], "")))
        if ts is None:
            print(f"[SKIP] Invalid timestamp row: {row}")
            return

        sip = str(row.get(self.cols["src_ip"], ""))
        dip = str(row.get(self.cols["dst_ip"], ""))
        sport = str(row.get(self.cols["src_port"], ""))
        dport = str(row.get(self.cols["dst_port"], ""))
        proto = str(row.get(self.cols["protocol"], "")).upper().strip()

        if not self._filter_packet(proto, sport, dport):
            return

        key = canonical_key(sip, sport, dip, dport, proto)
        now_ts = ts

        with self._state_lock:
            af = self.active.get(key)

            if af is None:
                # start new flow
                fid = make_flow_id(key, start_ts=now_ts)
                rel = Path("open") / f"{fid}.csv"
                abs_path = self.out_dir / rel

                with self._file_locks[abs_path]:
                    is_new = not abs_path.exists()
                    with abs_path.open("a", newline="") as f:
                        w = csv.writer(f)
                        if is_new:
                            w.writerow(self.cols.values())
                        w.writerow([row[self.cols[k]] for k in self.cols.keys()])

                af = ActiveFlow(fid, key, now_ts, now_ts, 1, rel)
                self.active[key] = af
                print(f"[NEW FLOW] {fid}")
                return

            # existing flow → timeouts?
            idle = float(self.cfg["idle_timeout_sec"])
            active_to = float(self.cfg.get("active_timeout_sec") or 0)

            if (now_ts - af.last_seen_ts) > idle or (active_to and (now_ts - af.start_ts) > active_to):
                # finalize then start a new flow with this packet
                self._finalize(af)

                fid = make_flow_id(key, start_ts=now_ts)
                rel = Path("open") / f"{fid}.csv"
                abs_path = self.out_dir / rel
                with self._file_locks[abs_path]:
                    is_new = not abs_path.exists()
                    with abs_path.open("a", newline="") as f:
                        w = csv.writer(f)
                        if is_new:
                            w.writerow(self.cols.values())
                        w.writerow([row[self.cols[k]] for k in self.cols.keys()])
                af = ActiveFlow(fid, key, now_ts, now_ts, 1, rel)
                self.active[key] = af
                print(f"[RESTART FLOW] {fid}")
                return

            # append to current flow
            abs_path = self.out_dir / af.csv_rel_path
            with self._file_locks[abs_path]:
                with abs_path.open("a", newline="") as f:
                    w = csv.writer(f)
                    w.writerow([row[self.cols[k]] for k in self.cols.keys()])
            af.packet_count += 1
            af.last_seen_ts = now_ts
            print(f"[APPEND] {af.flow_id}: packet #{af.packet_count}")

    def flush_timeouts(self, now_ts: float):
        idle = float(self.cfg["idle_timeout_sec"])
        to_finalize = []
        with self._state_lock:
            for key, af in list(self.active.items()):
                if (now_ts - af.last_seen_ts) > idle:
                    to_finalize.append(key)
            for key in to_finalize:
                af = self.active[key]
                self._finalize(af)
                del self.active[key]
                print(f"[FLUSH] {af.flow_id} idle={now_ts - af.last_seen_ts:.2f}s")

    def _finalize(self, af: ActiveFlow):
        src = self.out_dir / af.csv_rel_path
        dst = self.out_dir / "final" / src.name
        with self._file_locks[src]:
            try:
                os.replace(src, dst)
            except Exception as e:
                print(f"[WARN] Could not move {af.flow_id}: {e}")
        print(f"[SAVE] Flow {af.flow_id} → {dst}")

# -------------------------------------------------------------------------
# Threaded tailer with pool
# -------------------------------------------------------------------------
def tail_loop(cfg: dict, stop_event: Optional[threading.Event] = None):
    csv_path = Path(cfg["csv_path"]).resolve()
    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    tracker = FlowTracker(cfg)

    last_off = 0
    header_cache = None
    print(f"[INIT] Watching {csv_path}")

    with ThreadPoolExecutor(max_workers=cfg["max_threads"]) as executor:
        futures = []

        while True:
            # ✅ Stop gracefully when FastAPI shutdown triggers stop_event
            if stop_event and stop_event.is_set():
                print("[TAIL] Stop event received, shutting down tail_loop...")
                break

            try:
                if not csv_path.exists():
                    print("[WAIT] No CSV yet...")
                    time.sleep(cfg["poll_interval_sec"])
                    continue

                stat = csv_path.stat()
                if stat.st_size < last_off:
                    print("[RESET] File truncated/rotated, starting from 0")
                    last_off = 0
                    header_cache = None

                with csv_path.open("r", newline="") as f:
                    if last_off == 0:
                        header_cache = next(csv.reader(f), None)
                        if header_cache is None:
                            time.sleep(cfg["poll_interval_sec"])
                            continue
                    f.seek(last_off)

                    reader = csv.DictReader(f, fieldnames=header_cache if last_off > 0 else None)
                    for row in reader:
                        if row.get("timestamp") == "timestamp":
                            continue
                        futures.append(executor.submit(tracker.add_packet, row))

                    last_off = f.tell()

                tracker.flush_timeouts(time.time())
                futures = [ft for ft in futures if not ft.done()]

                print(f"[POOL] queued_or_running_tasks={len(futures)}  open_flows={len(tracker.active)}  last_off={last_off}")

            except Exception as e:
                print(f"[ERROR] {e}")

            time.sleep(cfg["poll_interval_sec"])


if __name__ == "__main__":
    Path(CONFIG["output_dir"]).mkdir(parents=True, exist_ok=True)
    tail_loop(CONFIG)
