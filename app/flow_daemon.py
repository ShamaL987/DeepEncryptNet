#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Optional

# ---------- CONFIG ----------
CONFIG = {
    # Use a raw string (r"...") or double backslashes on Windows!
    "csv_path": r"D:\FYP_DEV\AIMchat2.csv",
    "poll_interval_sec": 2.0,
    "idle_timeout_sec": 15.0,
    "active_timeout_sec": 1800.0,  # 30m
    "https_only": False,            # only flows where either port == 443
    "protocol_filter": ["TCP","UDP"],    # or ["TCP","UDP"]
    "output_dir": "app/data/extracted1",
    "columns": {
        "timestamp": "timestamp",
        "src_ip": "src_ip",
        "src_port": "src_port",
        "dst_ip": "dst_ip",
        "dst_port": "dst_port",
        "protocol": "protocol",
    }
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
    csv_rel_path: Path  # where we append packets for this flow

def canonical_key(sip: str, sport: str, dip: str, dport: str, proto: str) -> FiveKey:
    proto = proto.upper()
    a = (sip, sport); b = (dip, dport)
    low, high = (a, b) if a <= b else (b, a)
    return (low[0], low[1], high[0], high[1], proto)

import re

def make_flow_id(key: FiveKey, start_ts: float) -> str:
    sip, sport, dip, dport, proto = key
    fid = f"{proto}-{sip}_{sport}--{dip}_{dport}__{int(start_ts*1000)}"
    # Replace any remaining invalid filename characters just in case
    fid = re.sub(r'[<>:"/\\|?*]', '_', fid)
    return fid



class FlowTracker:
    """DB-free tracker; writes per-flow CSVs and prints progress."""
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.cols = cfg["columns"]
        self.out_dir = Path(cfg["output_dir"])
        (self.out_dir / "open").mkdir(parents=True, exist_ok=True)
        (self.out_dir / "final").mkdir(parents=True, exist_ok=True)
        self.active: Dict[FiveKey, ActiveFlow] = {}

    def _filter_packet(self, proto: str, sport: str, dport: str) -> bool:
        if self.cfg["protocol_filter"] and proto.upper() not in [p.upper() for p in self.cfg["protocol_filter"]]:
            return False
        if self.cfg["https_only"]:
            if sport != "443" and dport != "443":
                return False
        return True

    def add_packet(self, row: dict):
        from datetime import datetime

        try:
            raw_ts = row[self.cols["timestamp"]]
            # Try fast numeric path first
            try:
                ts = float(raw_ts)
            except ValueError:
                # Try parsing ISO or common datetime strings
                try:
                    ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00")).timestamp()
                except Exception:
                    # Fallback: try pandas parser if needed
                    import pandas as pd
                    ts = pd.to_datetime(raw_ts, errors="coerce").value / 1e9
                    if pd.isna(ts):
                        raise ValueError("Unparseable timestamp")
        except Exception:
            print(f"[SKIP] Invalid timestamp row: {row}")
            return

        sip = str(row[self.cols["src_ip"]])
        dip = str(row[self.cols["dst_ip"]])
        sport = str(row[self.cols["src_port"]])
        dport = str(row[self.cols["dst_port"]])
        proto = str(row[self.cols["protocol"]]).upper().strip()

        if not self._filter_packet(proto, sport, dport):
            return

        key = canonical_key(sip, sport, dip, dport, proto)
        now_ts = ts
        af = self.active.get(key)

        if af is None:
            # New flow start
            fid = make_flow_id(key, start_ts=now_ts)
            rel = Path("open") / f"{fid}.csv"
            abs_path = self.out_dir / rel
            is_new = not abs_path.exists()
            with abs_path.open("a", newline="") as f:
                w = csv.writer(f)
                if is_new:
                    # write header in configured order
                    w.writerow(self.cols.values())
                w.writerow([row[self.cols[k]] for k in self.cols.keys()])
            af = ActiveFlow(fid, key, now_ts, now_ts, 1, rel)
            self.active[key] = af
            print(f"[NEW FLOW] {fid}")
            return

        # existing flow — check timeouts
        idle = self.cfg["idle_timeout_sec"]
        active_to = float(self.cfg.get("active_timeout_sec") or 0)

        if (now_ts - af.last_seen_ts) > idle or (active_to and (now_ts - af.start_ts) > active_to):
            print(f"[FINALIZE] {af.flow_id} packets={af.packet_count} idle={now_ts - af.last_seen_ts:.2f}s")
            self._finalize(af)
            # start new flow with this packet
            fid = make_flow_id(key, start_ts=now_ts)
            rel = Path("open") / f"{fid}.csv"
            abs_path = self.out_dir / rel
            with abs_path.open("a", newline="") as f:
                w = csv.writer(f)
                w.writerow(self.cols.values())
                w.writerow([row[self.cols[k]] for k in self.cols.keys()])
            af = ActiveFlow(fid, key, now_ts, now_ts, 1, rel)
            self.active[key] = af
            print(f"[RESTART FLOW] {fid}")
            return

        # append packet
        abs_path = self.out_dir / af.csv_rel_path
        with abs_path.open("a", newline="") as f:
            w = csv.writer(f)
            w.writerow([row[self.cols[k]] for k in self.cols.keys()])
        af.packet_count += 1
        af.last_seen_ts = now_ts
        print(f"[APPEND] {af.flow_id}: packet #{af.packet_count}")

    def flush_timeouts(self, now_ts: float):
        idle = self.cfg["idle_timeout_sec"]
        to_finalize = []
        for key, af in list(self.active.items()):
            if (now_ts - af.last_seen_ts) > idle:
                to_finalize.append(key)
        for key in to_finalize:
            af = self.active[key]
            self._finalize(af)
            print(f"[FLUSH] {af.flow_id} idle={now_ts - af.last_seen_ts:.2f}s")
            del self.active[key]

    def _finalize(self, af: ActiveFlow):
        src = self.out_dir / af.csv_rel_path
        dst = self.out_dir / "final" / src.name
        try:
            os.replace(src, dst)
        except Exception as e:
            print(f"[WARN] Could not move {af.flow_id}: {e}")
        print(f"[SAVE] Flow {af.flow_id} → {dst}")


def tail_loop(cfg: dict, stop_event: Optional["threading.Event"] = None):
    """
    CSV tail loop. Reads new rows, updates flows, finalizes on idle.
    stop_event: optional threading.Event for graceful shutdown.
    """
    # Lazy import to avoid circular when FastAPI imports this module
    import threading  # noqa: F401

    csv_path = Path(cfg["csv_path"]).resolve()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    out_dir = Path(cfg["output_dir"]); out_dir.mkdir(parents=True, exist_ok=True)
    tracker = FlowTracker(cfg)
    last_off = 0
    header_cache = None

    print(f"[INIT] Watching {csv_path}")

    while True:
        if stop_event and stop_event.is_set():
            print("[STOP] stop_event set, exiting tail loop...")
            break

        try:
            if not csv_path.exists():
                print("[WAIT] No CSV yet...")
                _sleep(stop_event, cfg["poll_interval_sec"])
                continue

            stat = csv_path.stat()
            if stat.st_size < last_off:
                print("[RESET] File truncated/rotated, starting from 0")
                last_off = 0
                header_cache = None

            with csv_path.open("r", newline="") as f:
                if last_off == 0:
                    # Read header once
                    header_cache = next(csv.reader(f), None)
                    print(f"[HEADER] {header_cache}")
                f.seek(last_off)
                # If resuming mid-file, provide fieldnames so DictReader doesn't
                # treat the first data row as header.
                reader = csv.DictReader(f, fieldnames=header_cache if last_off > 0 else None)

                for row in reader:
                    # Guard: skip header lines that slip through
                    if row.get("timestamp") == "timestamp":
                        continue
                    tracker.add_packet(row)

                last_off = f.tell()

            now_ts = time.time()
            tracker.flush_timeouts(now_ts)
            print(f"[CHECKPOINT] last_off={last_off} size={stat.st_size} active_flows={len(tracker.active)}")

        except Exception as e:
            print(f"[ERROR] {e}")

        _sleep(stop_event, cfg["poll_interval_sec"])


def _sleep(stop_event: Optional["threading.Event"], seconds: float):
    if not stop_event:
        time.sleep(seconds)
        return
    # responsive sleep
    remaining = float(seconds)
    step = 0.1
    while remaining > 0 and not stop_event.is_set():
        time.sleep(min(step, remaining))
        remaining -= step


if __name__ == "__main__":
    Path(CONFIG["output_dir"]).mkdir(parents=True, exist_ok=True)
    tail_loop(CONFIG)
