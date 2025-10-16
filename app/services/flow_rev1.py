#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Optional

# ---------- CONFIG (replace with YAML loader if you prefer now) ----------
CONFIG = {
    "csv_path": "app/data/source.csv",
    "poll_interval_sec": 2.0,
    "idle_timeout_sec": 15.0,
    "active_timeout_sec": 1800.0,  # 30m split like NetFlow; set 0 to disable
    "https_only": True,            # only flows where either port == 443
    "protocol_filter": ["TCP"],    # or ["TCP","UDP"]
    "output_dir": "app/data/extracted",
    "db_path": "app/data/flow_state.db",
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

FiveKey = Tuple[str, str, str, str, str]  # canonical (sip, sport, dip, dport, PROTO)

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

def make_flow_id(key: FiveKey, start_ts: float) -> str:
    sip, sport, dip, dport, proto = key
    return f"{proto}-{sip}:{sport}__{dip}:{dport}__{int(start_ts*1000)}"

class StateDB:
    def __init__(self, path: Path):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS checkpoint(
            id INTEGER PRIMARY KEY CHECK (id=1),
            file_path TEXT NOT NULL,
            file_inode TEXT,
            file_mtime REAL,
            byte_offset INTEGER NOT NULL
        );
        INSERT OR IGNORE INTO checkpoint(id, file_path, file_inode, file_mtime, byte_offset)
        VALUES (1, '', NULL, NULL, 0);

        CREATE TABLE IF NOT EXISTS flows(
            flow_id TEXT PRIMARY KEY,
            proto TEXT, sip TEXT, sport TEXT, dip TEXT, dport TEXT,
            start_ts REAL, end_ts REAL,
            packet_count INTEGER,
            status TEXT,          -- 'finalized'
            csv_path TEXT
        );

        CREATE TABLE IF NOT EXISTS active_flows(
            flow_id TEXT PRIMARY KEY,
            proto TEXT, sip TEXT, sport TEXT, dip TEXT, dport TEXT,
            start_ts REAL, last_seen_ts REAL,
            packet_count INTEGER,
            csv_path TEXT
        );
        """)
        self.conn.commit()

    # ---- checkpoint ----
    def load_checkpoint(self) -> Tuple[str, Optional[str], Optional[float], int]:
        row = self.conn.execute("SELECT file_path, file_inode, file_mtime, byte_offset FROM checkpoint WHERE id=1").fetchone()
        return row[0], row[1], row[2], int(row[3])

    def save_checkpoint(self, file_path: str, inode: str, mtime: float, byte_offset: int):
        self.conn.execute(
            "UPDATE checkpoint SET file_path=?, file_inode=?, file_mtime=?, byte_offset=? WHERE id=1",
            (file_path, inode, mtime, byte_offset)
        )
        self.conn.commit()

    # ---- active flows ----
    def upsert_active(self, af: ActiveFlow):
        sip, sport, dip, dport, proto = af.key
        self.conn.execute("""
            INSERT INTO active_flows(flow_id, proto, sip, sport, dip, dport, start_ts, last_seen_ts, packet_count, csv_path)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(flow_id) DO UPDATE SET
              last_seen_ts=excluded.last_seen_ts,
              packet_count=excluded.packet_count
        """, (af.flow_id, proto, sip, sport, dip, dport, af.start_ts, af.last_seen_ts, af.packet_count, str(af.csv_rel_path)))
        self.conn.commit()

    def finalize_flow(self, af: ActiveFlow):
        sip, sport, dip, dport, proto = af.key
        self.conn.execute("""
            INSERT OR REPLACE INTO flows(flow_id, proto, sip, sport, dip, dport, start_ts, end_ts, packet_count, status, csv_path)
            VALUES(?,?,?,?,?,?,?,?,?,'finalized',?)
        """, (af.flow_id, proto, sip, sport, dip, dport, af.start_ts, af.last_seen_ts, af.packet_count, str(af.csv_rel_path)))
        self.conn.execute("DELETE FROM active_flows WHERE flow_id=?", (af.flow_id,))
        self.conn.commit()

class FlowTracker:
    def __init__(self, cfg: dict, db: StateDB):
        self.cfg = cfg
        self.db = db
        self.cols = cfg["columns"]
        self.out_dir = Path(cfg["output_dir"])
        (self.out_dir / "open").mkdir(parents=True, exist_ok=True)   # where active flow CSVs live
        (self.out_dir / "final").mkdir(parents=True, exist_ok=True)  # finalized flows
        self.active: Dict[FiveKey, ActiveFlow] = {}  # key -> ActiveFlow

    def _filter_packet(self, proto: str, sport: str, dport: str) -> bool:
        if self.cfg["protocol_filter"] and proto.upper() not in [p.upper() for p in self.cfg["protocol_filter"]]:
            return False
        if self.cfg["https_only"]:
            if sport != "443" and dport != "443":
                return False
        return True

    def add_packet(self, row: dict):
        # read fields as strings
        ts  = float(row[self.cols["timestamp"]])
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
            # new flow
            fid = make_flow_id(key, start_ts=now_ts)
            # write active CSV header if new
            rel = Path("open") / f"{fid}.csv"
            abs_path = self.out_dir / rel
            is_new = not abs_path.exists()
            with abs_path.open("a", newline="") as f:
                w = csv.writer(f)
                if is_new:
                    w.writerow(self.cols.values())  # header in the configured order
                w.writerow([row[self.cols[k]] for k in ["timestamp","src_ip","src_port","dst_ip","dst_port","protocol"]])
            af = ActiveFlow(flow_id=fid, key=key, start_ts=now_ts, last_seen_ts=now_ts, packet_count=1, csv_rel_path=rel)
            self.active[key] = af
            self.db.upsert_active(af)
            return

        # existing flow → check active/idle timeout
        idle = self.cfg["idle_timeout_sec"]
        active_to = float(self.cfg.get("active_timeout_sec") or 0)

        if (now_ts - af.last_seen_ts) > idle or (active_to and (now_ts - af.start_ts) > active_to):
            # finalize old flow
            self._finalize(af)
            # start a new one with this packet
            fid = make_flow_id(key, start_ts=now_ts)
            rel = Path("open") / f"{fid}.csv"
            abs_path = self.out_dir / rel
            is_new = not abs_path.exists()
            with abs_path.open("a", newline="") as f:
                w = csv.writer(f)
                if is_new:
                    w.writerow(self.cols.values())
                w.writerow([row[self.cols[k]] for k in ["timestamp","src_ip","src_port","dst_ip","dst_port","protocol"]])
            af = ActiveFlow(flow_id=fid, key=key, start_ts=now_ts, last_seen_ts=now_ts, packet_count=1, csv_rel_path=rel)
            self.active[key] = af
            self.db.upsert_active(af)
            return

        # continue current flow
        abs_path = self.out_dir / af.csv_rel_path
        with abs_path.open("a", newline="") as f:
            w = csv.writer(f)
            w.writerow([row[self.cols[k]] for k in ["timestamp","src_ip","src_port","dst_ip","dst_port","protocol"]])

        af.packet_count += 1
        af.last_seen_ts = now_ts
        self.db.upsert_active(af)

    def flush_timeouts(self, now_ts: float):
        """Finalize idle flows (no packets recently)."""
        idle = self.cfg["idle_timeout_sec"]
        to_finalize = []
        for key, af in self.active.items():
            if (now_ts - af.last_seen_ts) > idle:
                to_finalize.append(key)
        for key in to_finalize:
            self._finalize(self.active[key])
            del self.active[key]

    def _finalize(self, af: ActiveFlow):
        # move CSV from open/ → final/ (rename)
        src = self.out_dir / af.csv_rel_path
        dst = self.out_dir / "final" / src.name
        try:
            os.replace(src, dst)
            af.csv_rel_path = Path("final") / src.name
        except Exception:
            # if move fails, keep original path; still finalize metadata
            pass
        self.db.finalize_flow(af)

def tail_loop(cfg: dict):
    csv_path = Path(cfg["csv_path"]).resolve()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    out_dir = Path(cfg["output_dir"]); out_dir.mkdir(parents=True, exist_ok=True)

    db = StateDB(Path(cfg["db_path"]))
    tracker = FlowTracker(cfg, db)

    # checkpoint
    cp_path, cp_inode, cp_mtime, cp_off = db.load_checkpoint()
    last_off = cp_off if cp_path == str(csv_path) else 0

    # main loop
    while True:
        try:
            if not csv_path.exists():
                time.sleep(cfg["poll_interval_sec"])
                continue

            stat = csv_path.stat()
            inode = f"{stat.st_dev}-{stat.st_ino}" if hasattr(stat, "st_ino") else f"{stat.st_dev}-{stat.st_size}"
            mtime = stat.st_mtime

            # detect truncation/rotation
            if (cp_path != str(csv_path)) or (cp_inode and cp_inode != inode) or (stat.st_size < last_off):
                last_off = 0

            with csv_path.open("r", newline="") as f:
                f.seek(last_off)
                reader = csv.DictReader(f)
                for row in reader:
                    tracker.add_packet(row)
                last_off = f.tell()

            # checkpoint update
            db.save_checkpoint(str(csv_path), inode, mtime, last_off)

            # flush idle flows
            now_ts = time.time()
            tracker.flush_timeouts(now_ts)

        except Exception as e:
            print(f"[flow-daemon] Error: {e}")

        time.sleep(cfg["poll_interval_sec"])

if __name__ == "__main__":
    Path(CONFIG["output_dir"]).mkdir(parents=True, exist_ok=True)
    tail_loop(CONFIG)
