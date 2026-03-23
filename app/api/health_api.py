from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Request, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import get_settings_manager_from_request, get_controller
from app.api.user_api import _get_current_user, _decrypt_api_token
from app.database.db import get_db
from app.pipeline.registry import get_pipeline_model_display_config
from app.services.health import calculate_pipeline_health_metrics

router = APIRouter(prefix="/health", tags=["Flow Daemon"])

class FlowDaemonConfigPayload(BaseModel):
    config: dict[str, Any]
    restart_if_running: bool = True


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
    settings_manager = get_settings_manager_from_request(request)
    controller = get_controller(request)

    settings_manager.reload()
    controller.update_config(settings_manager.get_flow_daemon_config())

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
    resolved_flow_config = settings_manager.get_flow_daemon_config()
    controller_result = controller.update_config(resolved_flow_config)

    restart_result = None
    if payload.restart_if_running and controller.is_running:
        restart_result = controller.restart()

    return {
        "message": "Flow daemon runtime config updated successfully",
        "runtime_flow_daemon_config": updated_runtime_config,
        "resolved_flow_daemon_config": resolved_flow_config,
        "controller_update": controller_result,
        "restart": restart_result,
    }

@router.get("/overview")
def get_flow_overview(request: Request, db: Session = Depends(get_db), authorization: Optional[str] = Header(default=None),
):
    controller = get_controller(request)
    settings_manager = get_settings_manager_from_request(request)

    runtime_config = settings_manager.get_runtime_config()
    pipline_name = runtime_config['flow_daemon'].get('feature_pipeline')

    current_user = _get_current_user(
        db=db,
        authorization=authorization,
        request=request,
    )
    readable_api_token = None
    if current_user.api_token_encrypted and not current_user.is_token_revoked:
        readable_api_token = _decrypt_api_token(current_user.api_token_encrypted, request)

    is_running = controller.is_running
    health = calculate_pipeline_health_metrics(db) if is_running else {}
    health["prediction_uptime_sec"] = controller.get_uptime_sec()

    return {
        "status": "running" if is_running else "stopped",
        "is_running": is_running,
        "runtime_config": runtime_config,
        "health": health,
        "pipline_config": get_pipeline_model_display_config(pipline_name),
        "api_token": readable_api_token,
    }
