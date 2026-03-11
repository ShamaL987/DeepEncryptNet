from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.flow_daemon_controller import FlowDaemonController
from app.settings import SettingsManager

router = APIRouter(prefix="/api/daemon", tags=["Flow Daemon"])



class FlowDaemonConfigPayload(BaseModel):
    config: dict[str, Any]
    restart_if_running: bool = False


def get_controller(request: Request) -> FlowDaemonController:
    controller = getattr(request.app.state, "flow_daemon_controller", None)
    if controller is None:
        raise HTTPException(status_code=500, detail="Flow daemon controller is not initialized")
    return controller


def get_settings_manager_from_request(request: Request) -> SettingsManager:
    settings_manager = getattr(request.app.state, "settings_manager", None)
    if settings_manager is None:
        raise HTTPException(status_code=500, detail="Settings manager is not initialized")
    return settings_manager


@router.get("/status")
def get_flow_daemon_status(request: Request):
    controller = get_controller(request)
    settings_manager = get_settings_manager_from_request(request)

    return {
        "status": "running" if controller.is_running else "stopped",
        "is_running": controller.is_running,
        "config": settings_manager.get_runtime_config(),
    }


@router.post("/start")
def start_flow_daemon(request: Request):
    controller = get_controller(request)
    return controller.start()


@router.post("/stop")
def stop_flow_daemon(request: Request):
    controller = get_controller(request)
    return controller.stop()


@router.post("/restart")
def restart_flow_daemon(request: Request):
    controller = get_controller(request)
    return controller.restart()


@router.get("/config")
def get_flow_daemon_config(request: Request):
    settings_manager = get_settings_manager_from_request(request)
    return {
        "runtime_json_path": str(settings_manager.runtime_json_path),
        "runtime_config": settings_manager.get_runtime_config(),
        "runtime_flow_daemon": settings_manager.get_runtime_flow_daemon_config(),
        "resolved_flow_daemon": settings_manager.get_flow_daemon_config(),
    }

@router.put("/config")
def update_flow_daemon_config(payload: FlowDaemonConfigPayload, request: Request):
    settings_manager = get_settings_manager_from_request(request)
    controller = get_controller(request)

    updated_runtime_config = settings_manager.update_runtime_flow_daemon_config(payload.config)

    merged_flow_config = settings_manager.get_flow_daemon_config()
    result = controller.update_config(merged_flow_config)

    if payload.restart_if_running and controller.is_running:
        controller.restart()

    return {
        "message": "Flow daemon runtime config updated successfully",
        "config": updated_runtime_config,
        "result": result,
    }