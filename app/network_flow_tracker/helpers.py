from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple, List, Optional, Mapping

import numpy as np
import pandas as pd



FiveKey = Tuple[str, str, str, str, str]


@dataclass
class ActiveFlow:
    """Holds in-memory state for an active flow."""
    flow_id: str
    key: FiveKey
    start_ts: float
    last_seen_ts: float
    packet_count: int
    csv_rel_path: Path
    packet_times: List[Tuple[int, float, Optional[int]]] = field(default_factory=list)


def canonical_key(sip: str, sport: str, dip: str, dport: str, proto: str) -> FiveKey:
    """Returns a direction-agnostic 5-tuple key."""
    proto = proto.upper()
    a, b = (sip, sport), (dip, dport)
    low, high = (a, b) if a <= b else (b, a)
    return (low[0], low[1], high[0], high[1], proto)


def make_flow_id(key: FiveKey, start_ts: float) -> str:
    """Builds a stable file-safe flow identifier."""
    sip, sport, dip, dport, proto = key
    fid = f"{proto}-{sip}_{sport}--{dip}_{dport}__{int(start_ts * 1000)}"
    return re.sub(r'[<>:"/\\|?*]', "_", fid)


def _safe_int(v) -> Optional[int]:
    """Parses an integer or returns None."""
    try:
        return int(v)
    except Exception:
        return None


def _ts_to_seconds(series: pd.Series) -> pd.Series:
    """Coerces mixed timestamp formats to seconds."""
    ts_num = pd.to_numeric(series, errors="coerce")
    if ts_num.notna().mean() >= 0.9:
        med = np.nanmedian(ts_num)
        if med > 1e11:
            return (ts_num / 1e9).astype(float)
        elif med > 1e10:
            return (ts_num / 1e9).astype(float)
        elif med > 1e6:
            return (ts_num / 1e3).astype(float)
        else:
            return ts_num.astype(float)
    ts = pd.to_datetime(series, errors="coerce", utc=True)
    return ts.astype("int64") / 1e9


def _endpoint_key(ip_str: str, port_str: str) -> Tuple[Tuple[int, ...], int, str]:
    """Builds a sortable endpoint key for direction resolution."""
    try:
        ip = ipaddress.ip_address(ip_str)
        ip_tuple = tuple(int(b) for b in ip.packed)
    except Exception:
        ip_tuple = tuple(map(ord, ip_str))
    try:
        p = int(port_str)
    except Exception:
        p = 0
    return (ip_tuple, p, ip_str)


def _stable_fwd_mask(df: pd.DataFrame, cols: Mapping[str, str]) -> pd.Series:
    """Returns a mask for forward-direction packets."""
    sip = df[cols["src_ip"]].astype(str)
    dip = df[cols["dst_ip"]].astype(str)
    sport = df[cols["src_port"]].astype(str)
    dport = df[cols["dst_port"]].astype(str)
    a_key = _endpoint_key(sip.iloc[0], sport.iloc[0])
    b_key = _endpoint_key(dip.iloc[0], dport.iloc[0])
    low_is_src = a_key <= b_key
    if low_is_src:
        return (sip == sip.iloc[0]) & (sport == sport.iloc[0])
    else:
        return (sip == dip.iloc[0]) & (sport == dport.iloc[0])
