from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

from app.database.init_db import ensure_schema
from app.settings import get_settings, log
from app.flow_daemon import run_flow_daemon
from app.api.dashboard import router as dashboard_router


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

from fastapi.middleware.cors import CORSMiddleware

application.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

application.include_router(dashboard_router)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "static", "dashboard")

application.mount(
    "/assets",
    StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")),
    name="assets",
)

@application.get("/")
def serve_dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@application.get("/{path:path}")
def spa_fallback(path: str):
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Frontend not built"}
