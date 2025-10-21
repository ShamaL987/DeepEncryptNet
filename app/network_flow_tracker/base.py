from __future__ import annotations

import csv
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from app.settings import log
from app.network_flow_tracker.flow_tracker import FlowTracker


def tail_loop(cfg, stop_event: Optional[threading.Event] = None):
    """Tails a CSV stream and maintains per-flow state."""
    csv_path = Path(cfg.get("csv_path")).resolve()
    out_dir = Path(cfg.get("output_dir"))
    out_dir.mkdir(parents=True, exist_ok=True)
    tracker = FlowTracker(cfg)
    last_off = 0
    header_cache = None
    log.info(f"[INIT] Watching {csv_path}")
    with ThreadPoolExecutor(max_workers=cfg.get("max_threads")) as executor:
        futures = []
        try:
            while True:
                if stop_event and stop_event.is_set():
                    log.info("[TAIL] Stop signal received — shutting down.")
                    break
                if not csv_path.exists():
                    log.info("[WAIT] CSV not found, retrying...")
                    time.sleep(cfg.get("poll_interval_sec"))
                    continue
                stat = csv_path.stat()
                if stat.st_size < last_off:
                    log.warning("[RESET] File truncated/rotated — restarting from 0.")
                    last_off, header_cache = 0, None
                with csv_path.open("r", newline="") as f:
                    if last_off == 0:
                        header_cache = next(csv.reader(f), None)
                        if header_cache is None:
                            time.sleep(cfg.get("poll_interval_sec"))
                            continue
                        missing = [col for col in cfg.get("columns").values() if col not in header_cache]
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
                time.sleep(cfg.get("poll_interval_sec"))
        except Exception as e:
            log.exception(f"[ERROR] Unexpected exception in tail loop: {e}")
        finally:
            log.info("[TAIL] Final flush before shutdown...")
            tracker.flush_timeouts(time.time())
            log.info(f"[TAIL] Final stats: {tracker.stats}")
