from __future__ import annotations
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database.init_db import ensure_schema
import app.database.event_listeners # noqa: F401
from app.settings import get_settings, log
from app.network_flow_tracker import tail_loop

settings = get_settings()
FLOW_CFG = settings.get("flow_daemon")

_runner_thread: threading.Thread | None = None
_stop_event: threading.Event | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages startup and shutdown lifecycle."""
    global _runner_thread, _stop_event
    ensure_schema()
    _stop_event = threading.Event()
    _runner_thread = threading.Thread(target=tail_loop, args=(FLOW_CFG, _stop_event), daemon=True)
    log.info("[FastAPI] Starting flow daemon...")
    _runner_thread.start()
    try:
        yield
    finally:
        if _stop_event:
            log.info("[FastAPI] Stopping flow daemon...")
            _stop_event.set()
        if _runner_thread:
            _runner_thread.join(timeout=10)

app = FastAPI(title="DeepEncryptNet Flow Daemon", lifespan=lifespan)

@app.get("/status")
def status():
    """Reports daemon status and config paths."""
    alive = bool(_runner_thread and _runner_thread.is_alive())
    return {
        "daemon_running": alive,
        "csv_path": FLOW_CFG.get("csv_path"),
        "output_dir": FLOW_CFG.get("output_dir"),
        "stats_enabled": FLOW_CFG.get("enable_stats", False),
    }
