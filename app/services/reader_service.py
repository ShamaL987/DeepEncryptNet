from __future__ import annotations

import time
from collections import deque
from flow_con.futures import ThreadPoolExecutor, Future
from pathlib import Path
from typing import Callable, Dict, Tuple, Optional, Set

import pandas as pd

from app.config import Settings, load_settings

FiveTuple = Tuple[str, int, str, int, str]  # (src_ip, src_port, dst_ip, dst_port, "TCP")


class ReaderService:
    """
    Periodically reads the capture CSV and detects HTTPS/TCP stream 'starts'.
    For each start, it submits an extraction job to a thread pool (limited concurrency).

    Notes:
    - Prefer TCP SYN (if tcp_flags exists) else fallback to first-seen per 5-tuple in the new slice.
    - HTTPS assumed TCP/443 (configurable).
    - We prevent duplicates by ignoring flows that are currently running or recently closed.
    """

    def __init__(
        self,
        settings: Settings,
        on_start_extractor: Callable[[str, FiveTuple, pd.DataFrame], None],
    ) -> None:
        self.cfg = settings.reader
        self.on_start_extractor = on_start_extractor

        self.csv_path = Path(self.cfg.csv_path)
        self.cols = self.cfg.columns

        # Concurrency tracking
        self._running_flows: Set[FiveTuple] = set()        # flows currently being extracted
        self._futures: Dict[FiveTuple, Future] = {}

        # Short cooldown after extractor ends (avoid immediate retriggers)
        self._recent_closed: deque[tuple[FiveTuple, float]] = deque()
        self._recent_ttl_sec: float = 5.0  # configurable if you like

        # State for incremental reads
        self._last_row_count: int = 0

        # Pool
        self._pool = ThreadPoolExecutor(max_workers=self.cfg.max_concurrent_extractors)

    # ---------------------- public API ----------------------

    def run_forever(self) -> None:
        """Blocking loop. Polls the CSV, detects starts, and submits extractors."""
        self._ensure_csv_available()

        while True:
            try:
                new_rows = self._read_new_rows()
                if new_rows is not None and not new_rows.empty:
                    starts = self._detect_starts(new_rows)
                    self._submit_extractors(starts, full_df_slice=new_rows)
                self._harvest_done()
            except Exception as e:
                print(f"[ReaderService] Error: {e}")
            time.sleep(self.cfg.poll_interval_sec)

    # ---------------------- internals -----------------------

    def _ensure_csv_available(self) -> None:
        """Wait until the CSV file exists (safe start)."""
        print(f"[ReaderService] Waiting for CSV: {self.csv_path}")
        while not self.csv_path.exists():
            time.sleep(0.5)
        print(f"[ReaderService] Found CSV: {self.csv_path}")

    def _read_new_rows(self) -> Optional[pd.DataFrame]:
        """
        Incremental read: load full CSV and slice the new region since last read.
        If start_at_end is True and this is the first read, start from EOF (tail mode).
        """
        try:
            df = pd.read_csv(self.csv_path)
        except Exception as e:
            print(f"[ReaderService] read_csv error: {e}")
            return None

        total = len(df)
        if total == 0:
            return None

        # Tail mode on very first read (default False to make dev easier)
        start_at_end = getattr(self.cfg, "start_at_end", False)
        if self._last_row_count == 0 and start_at_end:
            self._last_row_count = total
            return None

        # Handle rotation/truncation
        if self._last_row_count > total:
            print("[ReaderService] Detected CSV truncation/rotation; resetting pointer.")
            self._last_row_count = 0

        if self._last_row_count == total:
            return None

        new_df = df.iloc[self._last_row_count:].copy()
        new_df.index.name = "orig_index"
        self._last_row_count = total
        return new_df

    def _purge_recent_closed(self, now: float) -> None:
        """Remove flows from the cooldown queue that have expired."""
        while self._recent_closed and (now - self._recent_closed[0][1]) > self._recent_ttl_sec:
            self._recent_closed.popleft()

    def _detect_starts(self, df: pd.DataFrame) -> Dict[FiveTuple, int]:
        """
        Fast start detection on the *new slice only*:
          - Filter TCP & port 443 (src or dst)
          - If tcp_flags present & require_syn_for_start: pick rows with SYN w/out ACK
          - Else: first-seen per 5-tuple in this new slice
        Returns {five_tuple: original_csv_row_index}.
        """
        required = [
            self.cols.src_ip, self.cols.src_port,
            self.cols.dst_ip, self.cols.dst_port,
            self.cols.protocol
        ]
        for col in required:
            if col not in df.columns:
                raise ValueError(f"Input CSV is missing required column: '{col}'")

        # Build a filtered candidate frame (vectorized)
        cand = df.loc[
            (df[self.cols.protocol].astype(str).str.upper() == "TCP") &
            (
                (df[self.cols.dst_port] == self.cfg.https_port) |
                (df[self.cols.src_port] == self.cfg.https_port)
            )
        ]
        if cand.empty:
            return {}

        # Vectorized 5-tuple key
        key_ser = (
            cand[self.cols.src_ip].astype(str) + "|" +
            cand[self.cols.src_port].astype(str) + "|" +
            cand[self.cols.dst_ip].astype(str) + "|" +
            cand[self.cols.dst_port].astype(str) + "|TCP"
        )

        # Ignore flows currently running or recently closed
        now = time.time()
        self._purge_recent_closed(now)
        running_keys = {
            f"{s}|{sp}|{d}|{dp}|TCP" for (s, sp, d, dp, _proto) in self._running_flows
        }
        cooldown_keys = {
            f"{s}|{sp}|{d}|{dp}|TCP" for (s, sp, d, dp, _proto), _t in self._recent_closed
        }
        inactive_mask = ~key_ser.isin(running_keys | cooldown_keys)
        cand = cand.loc[inactive_mask]
        key_ser = key_ser.loc[inactive_mask]
        if cand.empty:
            return {}

        starts: Dict[FiveTuple, int] = {}

        # Case A: SYN-only starts (if flags available & required)
        use_syn = (
            self.cfg.require_syn_for_start and
            (self.cols.tcp_flags is not None) and
            (self.cols.tcp_flags in cand.columns)
        )
        if use_syn:
            flags = cand[self.cols.tcp_flags].astype(str).str.upper().fillna("")
            syn_no_ack_mask = flags.str.contains("S") & ~flags.str.contains("A")
            cand_syn = cand.loc[syn_no_ack_mask]
            keys_syn = key_ser.loc[syn_no_ack_mask]
            if not cand_syn.empty:
                first_per_flow = cand_syn.loc[~keys_syn.duplicated(keep="first")]
                for idx, row in first_per_flow.iterrows():
                    five = (
                        str(row[self.cols.src_ip]), int(row[self.cols.src_port]),
                        str(row[self.cols.dst_ip]), int(row[self.cols.dst_port]),
                        "TCP",
                    )
                    starts[five] = int(idx)
                if starts:
                    return starts  # fast return

        # Case B: fallback to first-seen per 5-tuple in this slice
        first_per_flow = cand.loc[~key_ser.duplicated(keep="first")]
        for idx, row in first_per_flow.iterrows():
            five = (
                str(row[self.cols.src_ip]), int(row[self.cols.src_port]),
                str(row[self.cols.dst_ip]), int(row[self.cols.dst_port]),
                "TCP",
            )
            starts[five] = int(idx)

        return starts

    def _submit_extractors(self, starts: Dict[FiveTuple, int], full_df_slice: pd.DataFrame) -> None:
        """Submit extractor jobs for each new start, honoring concurrency limits and avoiding duplicates."""
        for five, start_idx in starts.items():
            if five in self._running_flows:
                continue
            if self._active_jobs() >= self.cfg.max_concurrent_extractors:
                break

            flow_id = self._make_flow_id(five, start_idx)
            df_for_flow = full_df_slice.copy()
            fut = self._pool.submit(self._run_extractor_safe, flow_id, five, df_for_flow)
            self._running_flows.add(five)
            self._futures[five] = fut
            print(f"[ReaderService] Submitted extractor for flow={flow_id}")

    def _run_extractor_safe(self, flow_id: str, five: FiveTuple, df_for_flow: pd.DataFrame) -> None:
        """Wrapper to call the extractor callback and always free the running slot."""
        try:
            self.on_start_extractor(flow_id, five, df_for_flow)
        except Exception as e:
            print(f"[ReaderService] Extractor error for {flow_id}: {e}")
        finally:
            self._running_flows.discard(five)
            self._futures.pop(five, None)
            self._recent_closed.append((five, time.time()))  # short cooldown

    def _harvest_done(self) -> None:
        """Clean up finished futures (best-effort)."""
        finished = [k for k, fut in self._futures.items() if fut.done()]
        for k in finished:
            self._running_flows.discard(k)
            self._futures.pop(k, None)

    def _active_jobs(self) -> int:
        return len(self._running_flows)

    @staticmethod
    def _make_flow_id(five: FiveTuple, start_index: int) -> str:
        s_ip, s_p, d_ip, d_p, proto = five
        return f"{proto}_{s_ip}:{s_p}->{d_ip}:{d_p}_row{start_index}"


# ----------------------- simple demo wiring -----------------------

def _demo_extractor(flow_id: str, five: FiveTuple, df_slice: pd.DataFrame) -> None:
    """
    Extract packets belonging only to this 5-tuple and save them to CSV.
    Uses column names from config and normalizes dtypes for robust matching.
    """
    from app.config import load_settings
    cols = load_settings().reader.columns

    start_t = time.time()

    # Resolve a stable output dir: <project_root>/app/data/extracted
    base_dir = Path(__file__).resolve().parents[2]
    extract_dir = base_dir / "app" / "data" / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)

    src_ip, src_port, dst_ip, dst_port, proto = five

    # ---- Normalize dtypes for reliable comparisons ----
    sip  = df_slice[cols.src_ip].astype(str)
    dip  = df_slice[cols.dst_ip].astype(str)
    sport = df_slice[cols.src_port].astype(str)
    dport = df_slice[cols.dst_port].astype(str)
    proto_ser = df_slice[cols.protocol].astype(str).str.upper()

    src_ip_s = str(src_ip)
    dst_ip_s = str(dst_ip)
    src_port_s = str(src_port)
    dst_port_s = str(dst_port)
    proto_s = str(proto).upper()

    # Match both directions of the same 5-tuple
    m_fwd = (sip == src_ip_s) & (sport == src_port_s) & (dip == dst_ip_s) & (dport == dst_port_s) & (proto_ser == proto_s)
    m_rev = (sip == dst_ip_s) & (sport == dst_port_s) & (dip == src_ip_s) & (dport == src_port_s) & (proto_ser == proto_s)
    mask = m_fwd | m_rev

    df_flow = df_slice.loc[mask].copy()

    if df_flow.empty:
        print(f"[Extractor] ⚠️ No packets matched {five}")
        return

    # Optional: sort by timestamp if present
    ts_col = cols.timestamp
    if ts_col in df_flow.columns:
        # coerce safe sort (doesn't error if mixed types)
        try:
            df_flow = df_flow.sort_values(by=ts_col)
        except Exception:
            pass

    # Safe filename
    safe_id = "".join(ch if ch.isalnum() or ch in ("_", "-", ".") else "_" for ch in flow_id)
    out_path = extract_dir / f"{safe_id}.csv"

    try:
        df_flow.to_csv(out_path, index=False)
        dur = time.time() - start_t
        print(f"[Extractor] Wrote {len(df_flow)} packets for {five} → {out_path} ({dur:.2f}s)")
    except Exception as e:
        print(f"[Extractor] ❌ Failed to write {out_path}: {e}")



if __name__ == "__main__":
    settings = load_settings()
    service = ReaderService(settings, on_start_extractor=_demo_extractor)
    service.run_forever()
