from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.database.init_db import ensure_schema
from app.settings import get_settings, log
from app.flow_daemon import run_flow_daemon

settings = get_settings()
FLOW_CFG = settings.get("flow_daemon", {})

_runner_thread: threading.Thread | None = None
_stop_event: threading.Event | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _runner_thread, _stop_event

    ensure_schema()

    _stop_event = threading.Event()
    _runner_thread = threading.Thread(
        target=run_flow_daemon,
        args=(FLOW_CFG, _stop_event),
        daemon=True,
        name="flow-daemon",
    )

    log.info("[FastAPI] Starting flow daemon")
    _runner_thread.start()

    try:
        yield
    finally:
        log.info("[FastAPI] Stopping flow daemon")
        if _stop_event:
            _stop_event.set()

        if _runner_thread:
            _runner_thread.join(timeout=10)
            if _runner_thread.is_alive():
                log.warning("[FastAPI] Flow daemon did not shut down cleanly")


application = FastAPI(
    title="DeepEncryptNet Flow Daemon",
    lifespan=lifespan,
)
