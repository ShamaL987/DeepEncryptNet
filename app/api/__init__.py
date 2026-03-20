from __future__ import annotations

from fastapi import HTTPException
from starlette.requests import Request

from app.services.flow_daemon_controller import FlowDaemonController
from app.settings import SettingsManager


def get_settings_manager_from_request(request: Request) -> SettingsManager:
    settings_manager = getattr(request.app.state, "settings_manager", None)
    if settings_manager is None:
        raise HTTPException(status_code=500, detail="Settings manager is not initialized")
    return settings_manager


def get_controller(request: Request) -> FlowDaemonController:
    controller = getattr(request.app.state, "flow_daemon_controller", None)
    if controller is None:
        raise HTTPException(status_code=500, detail="Flow daemon controller is not initialized")
    return controller

