from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/daemon", tags=["daemon"])


controller = None


def _model_info() -> dict[str, Any]:
    manifest = Path("app/pipeline/deepv14/logs/artifacts_manifest.json")
    if not manifest.exists():
        return {"manifest": None}

    try:
        with manifest.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"manifest": str(manifest), "error": "failed_to_parse"}

    return {
        "manifest": str(manifest),
        "artifacts": data.get("artifacts", {}),
        "created_at": data.get("created_at"),
    }


def set_daemon_controller(instance):
    global controller
    controller = instance


class ConfigUpdateRequest(BaseModel):
    poll_interval_sec: float | None = None
    idle_timeout_sec: float | None = None
    max_packets: int | None = None
    max_duration_sec: float | None = None
    enable_stats: bool | None = None


@router.get("/status")
def daemon_status(window_sec: int = Query(60, ge=10, le=3600)):
    if controller is None:
        raise HTTPException(status_code=503, detail="Daemon controller unavailable")

    snapshot = controller.stats_snapshot(window_sec=window_sec)
    return {
        "running": controller.is_running,
        "config": controller.get_config(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": _model_info(),
        "stats": {
            "window_sec": window_sec,
            "packets_per_sec": snapshot.packets_per_sec,
            "flows_per_sec": snapshot.flows_per_sec,
            "feature_latency_ms_avg": snapshot.feature_latency_ms_avg,
            "inference_latency_ms_avg": snapshot.inference_latency_ms_avg,
            "confidence_median": snapshot.confidence_median,
            "route_rate": snapshot.route_rate,
            "error_count": snapshot.error_count,
        },
    }


@router.get("/config")
def get_config():
    if controller is None:
        raise HTTPException(status_code=503, detail="Daemon controller unavailable")
    return controller.get_config()


@router.post("/config")
def update_config(request: ConfigUpdateRequest):
    if controller is None:
        raise HTTPException(status_code=503, detail="Daemon controller unavailable")

    updates: dict[str, Any] = {
        k: v for k, v in request.model_dump().items() if v is not None
    }
    config = controller.update_config(updates)
    return {"updated": list(updates.keys()), "config": config}


@router.post("/start")
def start_daemon():
    if controller is None:
        raise HTTPException(status_code=503, detail="Daemon controller unavailable")
    started = controller.start()
    return {"running": controller.is_running, "changed": started}


@router.post("/stop")
def stop_daemon():
    if controller is None:
        raise HTTPException(status_code=503, detail="Daemon controller unavailable")
    changed = controller.stop()
    return {"running": controller.is_running, "changed": changed}


@router.post("/restart")
def restart_daemon():
    if controller is None:
        raise HTTPException(status_code=503, detail="Daemon controller unavailable")
    controller.restart()
    return {"running": controller.is_running, "changed": True}
