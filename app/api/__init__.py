from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.database.models import PredictionResult, FlowRegistry
from app.services.flow_daemon_controller import FlowDaemonController
from app.settings import SettingsManager


LOW_CONFIDENCE_THRESHOLD = 0.60
ROUTING_SPIKE_THRESHOLD_PERCENT = 35.0
LOW_CONFIDENCE_MEDIAN_DROP = 0.10
QUEUE_GROWTH_ALERT_THRESHOLD = 10

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

def build_prediction_query(db: Session, pipeline_name: str | None):
    query = (
        db.query(PredictionResult)
        .join(FlowRegistry, PredictionResult.flow_id == FlowRegistry.flow_id)
    )
    if pipeline_name:
        query = query.filter(FlowRegistry.pipeline_name == pipeline_name)
    return query

