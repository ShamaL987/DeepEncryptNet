from __future__ import annotations
import threading
from fastapi import FastAPI

from app.flow_daemon import tail_loop, CONFIG, log
from app.database.init_db import ensure_schema
from app.database.event_listeners import trigger_prediction # noqa: F401



app = FastAPI(title="DeepEncryptNet Flow Daemon")

_runner_thread: threading.Thread | None = None
_stop_event: threading.Event | None = None

@app.on_event("startup")
def start_daemon():
    global _runner_thread, _stop_event
    ensure_schema()  # make sure flows_min & flow_stats exist
    if _runner_thread and _runner_thread.is_alive():
        return
    _stop_event = threading.Event()
    _runner_thread = threading.Thread(target=tail_loop, args=(CONFIG, _stop_event), daemon=True)
    log.info("[FastAPI] Starting flow daemon...")
    _runner_thread.start()

@app.on_event("shutdown")
def stop_daemon():
    global _runner_thread, _stop_event
    if _stop_event:
        log.info("[FastAPI] Stopping flow daemon...")
        _stop_event.set()
    if _runner_thread:
        _runner_thread.join(timeout=10)

@app.get("/status")
def status():
    alive = bool(_runner_thread and _runner_thread.is_alive())
    return {
        "daemon_running": alive,
        "csv_path": CONFIG["csv_path"],
        "output_dir": CONFIG["output_dir"],
        "stats_enabled": CONFIG.get("enable_stats", False),
    }
