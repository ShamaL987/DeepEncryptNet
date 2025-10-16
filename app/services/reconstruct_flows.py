#!/usr/bin/env python3
"""
Reconstruct bidirectional flows from a capture CSV using an idle-timeout split.

- Canonicalizes 5-tuples (direction-agnostic).
- Splits flows when inter-packet gap > idle_timeout_sec.
- Exports:
  * <out_dir>/flows_idle{N}s/summary.csv
  * <out_dir>/flows_idle{N}s/flows/flow_{id}.csv  (per-flow packets)

Usage examples:
  python reconstruct_flows.py --input path/to/master.csv --out out_dir --idle 15
  python reconstruct_flows.py --input path/to/master.csv --out out_dir --idle 5,10,15,30,120
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# --------------------------- column mapping helpers ---------------------------

def pick_col(df: pd.DataFrame, options: List[str]) -> str | None:
    col_map = {c.lower(): c for c in df.columns}
    for o in options:
        if o in df.columns:
            return o
        if o.lower() in col_map:
            return col_map[o.lower()]
    return None

def detect_columns(df: pd.DataFrame) -> Dict[str, str]:
    """Try to infer common column names (timestamp, IPs, ports, protocol)."""
    ts_col = pick_col(df, [
        "timestamp","time","ts","frame_time_epoch","frame.time_epoch",
        "arrival_time","capture_time","epoch_time","date","datetime"
    ]) or df.columns[0]
    proto_col = pick_col(df, ["protocol","proto","ip_proto","ip.proto"])
    if proto_col is None:
        df["__protocol"] = "TCP"
        proto_col = "__protocol"
    src_ip_col   = pick_col(df, ["src_ip","source_ip","ip.src","src ip","saddr"])
    dst_ip_col   = pick_col(df, ["dst_ip","destination_ip","ip.dst","dst ip","daddr"])
    src_port_col = pick_col(df, ["src_port","source_port","tcp.srcport","udp.srcport","src port","sport"])
    dst_port_col = pick_col(df, ["dst_port","destination_port","tcp.dstport","udp.dstport","dst port","dport"])
    required = [src_ip_col, dst_ip_col, src_port_col, dst_port_col, proto_col, ts_col]
    missing = [x for x in required if x is None]
    if missing:
        raise ValueError(f"Missing required columns (could not infer some of: src/dst IP, src/dst port, protocol, timestamp). Found: {list(df.columns)}")
    return dict(
        ts=ts_col, proto=proto_col,
        sip=src_ip_col, dip=dst_ip_col,
        sport=src_port_col, dport=dst_port_col,
    )

# --------------------------- core reconstruction -----------------------------

def parse_timestamps(df: pd.DataFrame, ts_col: str) -> pd.Series:
    """Return float seconds for the timestamp column, robust to numeric or datetime strings."""
    ts = df[ts_col]
    ts_num = pd.to_numeric(ts, errors="coerce")
    if ts_num.notna().mean() > 0.9:
        med = ts_num.median()
        if med > 1e11:        # ms
            seconds = ts_num / 1000.0
        elif med > 1e10:      # ns-ish big values -> assume ns
            seconds = ts_num / 1e9
        else:                 # seconds
            seconds = ts_num.astype(float)
    else:
        parsed = pd.to_datetime(ts, errors="coerce", utc=True)
        seconds = parsed.view("int64") / 1e9  # ns -> s
    return seconds

def canonical_key(row, sip, sport, dip, dport, proto) -> Tuple[str,str,str,str,str]:
    """Direction-agnostic flow key: sort (IP,port) pairs so fwd/rev map to same key."""
    a = (str(row[sip]), str(row[sport]))
    b = (str(row[dip]), str(row[dport]))
    pr = str(row[proto]).upper().strip()
    low, high = (a, b) if a <= b else (b, a)
    return (low[0], low[1], high[0], high[1], pr)

def reconstruct_flows(
    df: pd.DataFrame,
    cols: Dict[str,str],
    idle_timeout_sec: float,
) -> Tuple[pd.DataFrame, Dict[int, List[int]]]:
    """
    Reconstruct flows with a given idle timeout.
    Returns:
      flows_df: one row per flow with counts & times
      flow_rows: mapping flow_id -> list of row indices belonging to that flow
    """
    # Normalize protocol + timestamps
    df = df.copy()
    df["_proto"] = df[cols["proto"]].astype(str).str.upper().str.strip()
    df["_ts"] = parse_timestamps(df, cols["ts"])

    # Stable sort by time
    df = df.sort_values(by="_ts", kind="mergesort").reset_index(drop=True)

    # State
    active_last_seen: Dict[Tuple[str,str,str,str,str], float] = {}
    current_flow_id: Dict[Tuple[str,str,str,str,str], int] = {}
    flow_id_counter = 0
    flow_packet_counts = Counter()
    flow_first_last: Dict[int, List[object]] = {}  # fid -> [first_ts, last_ts, key]
    flow_rows: Dict[int, List[int]] = defaultdict(list)

    # Iterate
    for idx, row in df.iterrows():
        key = canonical_key(row, cols["sip"], cols["sport"], cols["dip"], cols["dport"], "_proto")
        t = float(row["_ts"])
        last = active_last_seen.get(key)
        if (last is None) or (t - last > idle_timeout_sec):
            # New flow for this key
            flow_id_counter += 1
            fid = flow_id_counter
            current_flow_id[key] = fid
            flow_packet_counts[fid] += 1
            flow_first_last[fid] = [t, t, key]
            flow_rows[fid].append(idx)
        else:
            # Continue existing flow
            fid = current_flow_id[key]
            flow_packet_counts[fid] += 1
            flow_first_last[fid][1] = t
            flow_rows[fid].append(idx)
        active_last_seen[key] = t

    # Build summary table
    rows = []
    for fid, (first_ts, last_ts, key) in flow_first_last.items():
        sip, sp, dip, dp, pr = key
        rows.append({
            "FlowID": fid,
            "Protocol": pr,
            "SrcIP": sip, "SrcPort": sp,
            "DstIP": dip, "DstPort": dp,
            "Packets": flow_packet_counts[fid],
            "StartTs": first_ts, "EndTs": last_ts,
            "Duration(s)": (last_ts - first_ts) if (pd.notna(first_ts) and pd.notna(last_ts)) else np.nan
        })

    flows_df = pd.DataFrame(rows).sort_values(by="Packets", ascending=False).reset_index(drop=True)
    return flows_df, flow_rows

# ------------------------------- I/O wrapper ---------------------------------

def export_results(
    df: pd.DataFrame,
    flows_df: pd.DataFrame,
    flow_rows: Dict[int, List[int]],
    out_dir: Path,
    idle: float,
) -> Path:
    """Write the summary CSV and per-flow packet CSVs for a given idle timeout."""
    base = out_dir / f"flows_idle{int(idle)}s"
    flows_path = base / "flows"
    base.mkdir(parents=True, exist_ok=True)
    flows_path.mkdir(parents=True, exist_ok=True)

    # Summary
    summary_csv = base / "summary.csv"
    flows_df.to_csv(summary_csv, index=False)

    # Per-flow CSVs
    for fid, idxs in flow_rows.items():
        sub = df.iloc[idxs].copy()
        sub.to_csv(flows_path / f"flow_{fid}.csv", index=False)

    return summary_csv

# --------------------------------- CLI ---------------------------------------

def parse_idle_list(s: str) -> List[float]:
    vals = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        vals.append(float(part))
    if not vals:
        vals = [15.0]
    return vals

def main():
    ap = argparse.ArgumentParser(description="Reconstruct bidirectional flows with idle-timeout splitting.")
    ap.add_argument("--input", required=True, help="Path to the master capture CSV.")
    ap.add_argument("--out",   required=True, help="Output directory for results.")
    ap.add_argument("--idle",  default="15", help="Idle timeout seconds; single value or comma list, e.g. '10,15,30,120'.")
    ap.add_argument("--show",  action="store_true", help="Print a brief summary per idle value.")
    args = ap.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out)

    df = pd.read_csv(input_path)
    cols = detect_columns(df)

    idle_values = parse_idle_list(args.idle)

    for idle in idle_values:
        flows_df, flow_rows = reconstruct_flows(df, cols, idle_timeout_sec=idle)
        summary_csv = export_results(df, flows_df, flow_rows, out_dir, idle)
        if args.show:
            print(f"[idle={idle:>5.1f}s] packets={len(df):4d} flows={len(flows_df):3d} avg_pkts/flow={flows_df['Packets'].mean():.2f}  -> {summary_csv}")

if __name__ == "__main__":
    main()
