from __future__ import annotations

from datetime import datetime
from typing import cast

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import Float, String, distinct, or_, cast as sql_cast, null
from sqlalchemy.orm import Session

from app.api import get_settings_manager_from_request
from app.database.db import get_db
from app.database.models import FlowRegistry
from app.database.models.https_flow_stats import HTTPSFlowStats
from app.database.models.iscx_flow_stats_v2 import ISCXFlowStatsV2
from app.database.models.prediction_results import PredictionResult
from app.services import utc_now
from app.services.routed_flows import normalize_dt

router = APIRouter(prefix="/live-flows", tags=["Live Flows"])


RELIABLE_CONFIDENCE_THRESHOLD = 0.75
RELIABLE_MARGIN_THRESHOLD = 0.20


def resolve_decision(action: int) -> str:
    return "Routed" if action == 1 else "Classified"


def resolve_reliability(action: int, confidence: float, margin: float) -> str:
    if action == 1:
        return "Unknown"
    if confidence >= RELIABLE_CONFIDENCE_THRESHOLD and margin >= RELIABLE_MARGIN_THRESHOLD:
        return "Reliable"
    return "Unreliable"


def build_reason(action: int, confidence: float, margin: float) -> str:
    if action == 1:
        return f"Confidence below threshold ({confidence:.2f}) → routed to unknown queue"
    if confidence >= RELIABLE_CONFIDENCE_THRESHOLD and margin >= RELIABLE_MARGIN_THRESHOLD:
        return f"High confidence classification ({confidence:.2f})"
    return f"Classified with moderate confidence ({confidence:.2f}) → review recommended"


@router.get("/overview")
def get_live_flows_overview(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    decision: str = Query(default="all"),
    predicted_class: str = Query(default="all"),
    reliability: str = Query(default="all"),
    alerts_only: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    now = utc_now()

    settings_manager = get_settings_manager_from_request(request)
    runtime_config = settings_manager.get_runtime_config()
    pipeline_name = runtime_config.get("flow_daemon", {}).get("feature_pipeline")

    base_query = (
        db.query(
            PredictionResult.flow_id,
            PredictionResult.created_at,
            PredictionResult.predicted_class,
            PredictionResult.action,
            PredictionResult.max_p,
            PredictionResult.entropy,
            PredictionResult.margin,
            PredictionResult.model_version,
            FlowRegistry.total_packets,
            FlowRegistry.total_bytes,
        )
        .join(FlowRegistry, PredictionResult.flow_id == FlowRegistry.flow_id)
    )

    if pipeline_name:
        base_query = base_query.filter(FlowRegistry.pipeline_name == pipeline_name)

    if pipeline_name == "HTTPS":
        base_query = (
            base_query
            .outerjoin(HTTPSFlowStats, PredictionResult.flow_id == HTTPSFlowStats.flow_id)
            .add_columns(
                sql_cast(HTTPSFlowStats.prefix_duration, Float).label("duration_sec"),
                sql_cast(null(), String).label("src_to_dst"),
                sql_cast(null(), String).label("protocol"),
            )
        )
    elif pipeline_name == "ISCX":
        base_query = (
            base_query
            .outerjoin(ISCXFlowStatsV2, PredictionResult.flow_id == ISCXFlowStatsV2.flow_id)
            .add_columns(
                sql_cast(ISCXFlowStatsV2.duration, Float).label("duration_sec"),
                sql_cast(null(), String).label("src_to_dst"),
                sql_cast(null(), String).label("protocol"),
            )
        )
    else:
        base_query = (
            base_query
            .add_columns(
                sql_cast(null(), Float).label("duration_sec"),
                sql_cast(null(), String).label("src_to_dst"),
                sql_cast(null(), String).label("protocol"),
            )
        )

    if decision.lower() == "classified":
        base_query = base_query.filter(PredictionResult.action != 1)
    elif decision.lower() == "routed":
        base_query = base_query.filter(PredictionResult.action == 1)

    if predicted_class.lower() != "all":
        base_query = base_query.filter(PredictionResult.predicted_class == predicted_class)

    if reliability.lower() == "unknown":
        base_query = base_query.filter(PredictionResult.action == 1)
    elif reliability.lower() == "reliable":
        base_query = base_query.filter(
            PredictionResult.action != 1,
            PredictionResult.max_p >= RELIABLE_CONFIDENCE_THRESHOLD,
            PredictionResult.margin >= RELIABLE_MARGIN_THRESHOLD,
        )
    elif reliability.lower() == "unreliable":
        base_query = base_query.filter(
            PredictionResult.action != 1,
            or_(
                PredictionResult.max_p < RELIABLE_CONFIDENCE_THRESHOLD,
                PredictionResult.margin < RELIABLE_MARGIN_THRESHOLD,
            ),
        )

    if alerts_only:
        base_query = base_query.filter(
            or_(
                PredictionResult.action == 1,
                PredictionResult.max_p < RELIABLE_CONFIDENCE_THRESHOLD,
                PredictionResult.margin < RELIABLE_MARGIN_THRESHOLD,
            )
        )

    rows = (
        base_query
        .order_by(PredictionResult.created_at.desc())
        .limit(limit)
        .all()
    )

    items = []

    for row in rows:
        created_at = normalize_dt(cast(datetime, row.created_at))
        confidence = float(row.max_p)
        margin = float(row.margin)
        action_value = int(row.action)

        decision_value = resolve_decision(action_value)
        reliability_value = resolve_reliability(
            action=action_value,
            confidence=confidence,
            margin=margin,
        )

        items.append(
            {
                "flow_id": str(row.flow_id),
                "timestamp": created_at.isoformat(),
                "src_to_dst": row.src_to_dst or "N/A",
                "protocol": row.protocol or "N/A",
                "total_packets": int(row.total_packets),
                "total_bytes": int(row.total_bytes),
                "duration_sec": float(row.duration_sec) if row.duration_sec is not None else None,
                "predicted_type": str(row.predicted_class),
                "confidence": confidence,
                "decision": decision_value,
                "reliability": reliability_value,
                "reason": build_reason(
                    action=action_value,
                    confidence=confidence,
                    margin=margin,
                ),
                "model_version": str(row.model_version) if row.model_version else "N/A",
                "age_sec": max(0, int((now - created_at).total_seconds())),
                "is_alert": decision_value == "Routed" or reliability_value == "Unreliable",
            }
        )

    classes_query = (
        db.query(distinct(PredictionResult.predicted_class))
        .join(FlowRegistry, PredictionResult.flow_id == FlowRegistry.flow_id)
    )

    if pipeline_name:
        classes_query = classes_query.filter(FlowRegistry.pipeline_name == pipeline_name)

    predicted_classes = sorted(
        [
            str(value)
            for (value,) in classes_query.all()
            if value is not None and str(value).strip()
        ]
    )

    total_count = len(items)
    classified_count = sum(1 for item in items if item["decision"] == "Classified")
    routed_count = sum(1 for item in items if item["decision"] == "Routed")
    reliable_count = sum(1 for item in items if item["reliability"] == "Reliable")
    unreliable_count = sum(1 for item in items if item["reliability"] == "Unreliable")
    unknown_count = sum(1 for item in items if item["reliability"] == "Unknown")
    alert_count = sum(1 for item in items if item["is_alert"])

    return {
        "items": items,
        "summary": {
            "total": total_count,
            "classified": classified_count,
            "routed": routed_count,
            "reliable": reliable_count,
            "unreliable": unreliable_count,
            "unknown": unknown_count,
            "alerts": alert_count,
        },
        "filter_options": {
            "decisions": ["All", "Classified", "Routed"],
            "reliabilities": ["All", "Reliable", "Unreliable", "Unknown"],
            "predicted_classes": ["All", *predicted_classes],
        },
    }