from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import cast

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import Float, cast as sql_cast, func, null
from sqlalchemy.orm import Session

from app.api.daemon_control import get_settings_manager_from_request
from app.database.db import get_db
from app.database.models import FlowRegistry
from app.database.models.https_flow_stats import HTTPSFlowStats
from app.database.models.iscx_flow_stats_v2 import ISCXFlowStatsV2
from app.database.models.prediction_results import PredictionResult
from app.services.health import utc_now
from app.services.routed_flows import compute_risk_status, normalize_dt

router = APIRouter(prefix="/api/routed-queue", tags=["Routed Queue"])


def build_grouping_suggestions(items: list[dict]) -> list[dict]:
    groups = {
        "Small flows (<10KB)": [item for item in items if item["total_bytes"] < 10 * 1024],
        "Medium duration (5-30s)": [
            item
            for item in items
            if item["duration_sec"] is not None and 5.0 <= item["duration_sec"] <= 30.0
        ],
        "Large flows (>1MB)": [item for item in items if item["total_bytes"] > 1024 * 1024],
    }

    suggestions = []

    for label, group_items in groups.items():
        if group_items:
            nearest_class = Counter(item["predicted_type"] for item in group_items).most_common(1)[0][0]
        else:
            nearest_class = "N/A"

        suggestions.append(
            {
                "label": label,
                "count": len(group_items),
                "nearest_class": nearest_class,
            }
        )

    return suggestions


@router.get("/overview")
def get_routed_queue_overview(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    now = utc_now()
    one_minute_ago = now - timedelta(minutes=1)

    settings_manager = get_settings_manager_from_request(request)
    runtime_config = settings_manager.get_runtime_config()
    pipeline_name = runtime_config.get("flow_daemon", {}).get("feature_pipeline")

    base_query = (
        db.query(
            PredictionResult.flow_id,
            PredictionResult.created_at,
            PredictionResult.predicted_class,
            PredictionResult.max_p,
            PredictionResult.entropy,
            PredictionResult.margin,
            FlowRegistry.total_packets,
            FlowRegistry.total_bytes,
        )
        .join(FlowRegistry, PredictionResult.flow_id == FlowRegistry.flow_id)
        .filter(PredictionResult.action == 1)
    )

    if pipeline_name:
        base_query = base_query.filter(FlowRegistry.pipeline_name == pipeline_name)

    if pipeline_name == "HTTPS":
        routed_rows = (
            base_query
            .add_columns(sql_cast(HTTPSFlowStats.prefix_duration, Float).label("duration_sec"))
            .outerjoin(HTTPSFlowStats, PredictionResult.flow_id == HTTPSFlowStats.flow_id)
            .order_by(PredictionResult.created_at.desc())
            .limit(limit)
            .all()
        )
    elif pipeline_name == "ISCX":
        routed_rows = (
            base_query
            .add_columns(sql_cast(ISCXFlowStatsV2.duration, Float).label("duration_sec"))
            .outerjoin(ISCXFlowStatsV2, PredictionResult.flow_id == ISCXFlowStatsV2.flow_id)
            .order_by(PredictionResult.created_at.desc())
            .limit(limit)
            .all()
        )
    else:
        routed_rows = (
            base_query
            .add_columns(sql_cast(null(), Float).label("duration_sec"))
            .order_by(PredictionResult.created_at.desc())
            .limit(limit)
            .all()
        )

    total_routed_query = (
        db.query(func.count(PredictionResult.id))
        .join(FlowRegistry, PredictionResult.flow_id == FlowRegistry.flow_id)
        .filter(PredictionResult.action == 1)
    )

    routed_last_min_query = (
        db.query(func.count(PredictionResult.id))
        .join(FlowRegistry, PredictionResult.flow_id == FlowRegistry.flow_id)
        .filter(
            PredictionResult.action == 1,
            PredictionResult.created_at >= one_minute_ago,
        )
    )

    avg_confidence_query = (
        db.query(func.avg(PredictionResult.max_p))
        .join(FlowRegistry, PredictionResult.flow_id == FlowRegistry.flow_id)
        .filter(PredictionResult.action == 1)
    )

    if pipeline_name:
        total_routed_query = total_routed_query.filter(FlowRegistry.pipeline_name == pipeline_name)
        routed_last_min_query = routed_last_min_query.filter(FlowRegistry.pipeline_name == pipeline_name)
        avg_confidence_query = avg_confidence_query.filter(FlowRegistry.pipeline_name == pipeline_name)

    total_routed = int(total_routed_query.scalar() or 0)
    routed_last_min = float(routed_last_min_query.scalar() or 0)
    avg_confidence = avg_confidence_query.scalar()

    items = []

    for row in routed_rows:
        created_at = normalize_dt(cast(datetime, row.created_at))
        confidence = float(row.max_p)

        items.append(
            {
                "flow_id": str(row.flow_id),
                "timestamp": created_at.isoformat(),
                "predicted_type": str(row.predicted_class),
                "confidence": confidence,
                "age_in_queue_sec": max(0, int((now - created_at).total_seconds())),
                "risk_status": compute_risk_status(
                    max_p=confidence,
                    entropy=float(row.entropy),
                    margin=float(row.margin),
                ),
                "total_packets": int(row.total_packets),
                "total_bytes": int(row.total_bytes),
                "duration_sec": float(row.duration_sec) if row.duration_sec is not None else None,
            }
        )

    return {
        "items": items,
        "grouping_suggestions": build_grouping_suggestions(items),
        "summary": {
            "queue_size": len(items),
            "routed_per_min": routed_last_min,
            "avg_confidence": float(avg_confidence) if avg_confidence is not None else None,
            "total_routed": total_routed,
        },
    }