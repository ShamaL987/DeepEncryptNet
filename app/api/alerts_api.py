from __future__ import annotations

from datetime import timedelta
from statistics import median

from fastapi import APIRouter, Depends, Request
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api import get_settings_manager_from_request, get_controller, build_prediction_query, \
    ROUTING_SPIKE_THRESHOLD_PERCENT, LOW_CONFIDENCE_MEDIAN_DROP, QUEUE_GROWTH_ALERT_THRESHOLD
from app.database.db import get_db

from app.database.models.prediction_results import PredictionResult
from app.services import utc_now

router = APIRouter(prefix="/alerts-on", tags=["Dashboard"])


def build_active_alerts(prediction_query, queue_size, now):
    alerts: list[dict] = []

    last_10_min_query = prediction_query.filter(
        PredictionResult.created_at >= now - timedelta(minutes=10)
    )
    last_10_total = int(
        last_10_min_query.with_entities(func.count(PredictionResult.id)).scalar() or 0
    )
    last_10_routed = int(
        last_10_min_query
        .filter(PredictionResult.action == 1)
        .with_entities(func.count(PredictionResult.id))
        .scalar()
        or 0
    )

    routed_percent_10m = (
        float(last_10_routed) / float(last_10_total) * 100.0
        if last_10_total > 0
        else 0.0
    )

    if routed_percent_10m > ROUTING_SPIKE_THRESHOLD_PERCENT:
        alerts.append(
            {
                "severity": "high",
                "title": "Routing Spike Detected",
                "message": (
                    f"Routed % exceeded {ROUTING_SPIKE_THRESHOLD_PERCENT:.0f}% in the last 10 minutes "
                    f"(currently {routed_percent_10m:.0f}%)"
                ),
                "timestamp": now.isoformat(),
            }
        )

    current_15_start = now - timedelta(minutes=15)
    previous_15_start = now - timedelta(minutes=30)

    current_15_conf = [
        float(value[0])
        for value in (
            prediction_query
            .filter(PredictionResult.created_at >= current_15_start)
            .with_entities(PredictionResult.max_p)
            .all()
        )
        if value[0] is not None
    ]

    previous_15_conf = [
        float(value[0])
        for value in (
            prediction_query
            .filter(
                PredictionResult.created_at >= previous_15_start,
                PredictionResult.created_at < current_15_start,
            )
            .with_entities(PredictionResult.max_p)
            .all()
        )
        if value[0] is not None
    ]

    if current_15_conf and previous_15_conf:
        current_median = median(current_15_conf)
        previous_median = median(previous_15_conf)

        if previous_median - current_median >= LOW_CONFIDENCE_MEDIAN_DROP:
            alerts.append(
                {
                    "severity": "medium",
                    "title": "Low Confidence Surge",
                    "message": (
                        f"Confidence median dropped from {previous_median:.2f} "
                        f"to {current_median:.2f} in the last 15 minutes"
                    ),
                    "timestamp": now.isoformat(),
                }
            )

    routed_last_5 = int(
        prediction_query
        .filter(
            PredictionResult.created_at >= now - timedelta(minutes=5),
            PredictionResult.action == 1,
        )
        .with_entities(func.count(PredictionResult.id))
        .scalar()
        or 0
    )

    if routed_last_5 >= QUEUE_GROWTH_ALERT_THRESHOLD:
        alerts.append(
            {
                "severity": "medium",
                "title": "Unknown Queue Growing",
                "message": (
                    f"Queue received {routed_last_5} routed flows in the last 5 minutes "
                    f"(current pending: {queue_size})"
                ),
                "timestamp": now.isoformat(),
            }
        )

    return alerts


@router.get("/alerts")
def get_dashboard_alerts(request: Request, db: Session = Depends(get_db)):
    controller = get_controller(request)
    settings_manager = get_settings_manager_from_request(request)

    runtime_config = settings_manager.get_runtime_config()
    pipeline_name = runtime_config["flow_daemon"].get("feature_pipeline")
    now = utc_now()

    prediction_query = build_prediction_query(db, pipeline_name)
    queue_size = controller.get_prediction_queue_count()

    alerts = build_active_alerts(prediction_query, queue_size, now)

    return {
        "items": alerts,
        "count": len(alerts),
        "has_alerts": len(alerts) > 0,
        "generated_at": now.isoformat(),
    }