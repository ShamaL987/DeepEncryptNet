from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles

from app.api.daemon_control import router as daemon_control_router
from app.database.init_db import ensure_schema
from app.services.flow_daemon_controller import FlowDaemonController
from app.settings import get_settings_manager, log


def create_application() -> FastAPI:
    settings_manager = get_settings_manager()
    flow_config = settings_manager.get_flow_daemon_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ensure_schema()

        app.state.settings_manager = settings_manager

        controller = FlowDaemonController(initial_config=flow_config)
        app.state.flow_daemon_controller = controller

        if bool(flow_config.get("auto_start", False)):
            log.info("[FastAPI] Auto-starting flow daemon")
            controller.start()

        try:
            yield
        finally:
            log.info("[FastAPI] Shutting down application")
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

    application.include_router(daemon_control_router)

    base_dir = Path(__file__).resolve().parent
    frontend_dir = base_dir / "static" / "dashboard"
    assets_dir = frontend_dir / "assets"

    if assets_dir.exists():
        application.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @application.get("/", include_in_schema=False)
    def serve_dashboard():
        index_path = frontend_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return JSONResponse({"detail": "Frontend not built"}, status_code=404)

    @application.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": "API route not found"}, status_code=404)

        index_path = frontend_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

        return JSONResponse({"detail": "Frontend not built"}, status_code=404)

    return application


application = create_application()