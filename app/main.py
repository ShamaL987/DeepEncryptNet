from __future__ import annotations

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

from app.database.init_db import ensure_schema
from app.settings import get_settings, log
from app.api.dashboard import router as dashboard_router
from app.api.daemon import router as daemon_router, set_daemon_controller
from app.services import DaemonController


settings = get_settings()
FLOW_CFG = settings.get("flow_daemon", {})
controller = DaemonController(initial_config=FLOW_CFG)
set_daemon_controller(controller)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_schema()

    controller.start()

    try:
        yield
    finally:
        log.info("[FastAPI] Stopping flow daemon")
        controller.stop()


application = FastAPI(
    title="DeepEncryptNet Flow Daemon",
    lifespan=lifespan,
)

application.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

application.include_router(dashboard_router)
application.include_router(daemon_router)

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
