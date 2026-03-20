from __future__ import annotations

from datetime import timedelta
from statistics import median

from fastapi import APIRouter, Depends, Request
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api import get_settings_manager_from_request, get_controller
from app.database.db import get_db
from app.database.models import FlowRegistry
from app.database.models.https_flow_stats import HTTPSFlowStats
from app.database.models.iscx_flow_stats_v2 import ISCXFlowStatsV2
from app.database.models.prediction_results import PredictionResult
from app.services.health import utc_now

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

LOW_CONFIDENCE_THRESHOLD = 0.60
ROUTING_SPIKE_THRESHOLD_PERCENT = 35.0
LOW_CONFIDENCE_MEDIAN_DROP = 0.10
QUEUE_GROWTH_ALERT_THRESHOLD = 10


def get_stats_model_for_pipeline(pipeline_name: str | None):
    if pipeline_name == "HTTPS":
        return HTTPSFlowStats
    if pipeline_name == "ISCX":
        return ISCXFlowStatsV2
    return None


def build_flow_query(db: Session, pipeline_name: str | None):
    query = db.query(FlowRegistry)
    if pipeline_name:
        query = query.filter(FlowRegistry.pipeline_name == pipeline_name)
    return query


def build_prediction_query(db: Session, pipeline_name: str | None):
    query = (
        db.query(PredictionResult)
        .join(FlowRegistry, PredictionResult.flow_id == FlowRegistry.flow_id)
    )
    if pipeline_name:
        query = query.filter(FlowRegistry.pipeline_name == pipeline_name)
    return query


def build_stats_query(db: Session, pipeline_name: str | None):
    stats_model = get_stats_model_for_pipeline(pipeline_name)
    if stats_model is None:
        return None, None

    query = (
        db.query(stats_model)
        .join(FlowRegistry, stats_model.flow_id == FlowRegistry.flow_id)
    )
    if pipeline_name:
        query = query.filter(FlowRegistry.pipeline_name == pipeline_name)

    return stats_model, query


def build_hourly_bucket_map(now, hours: int = 24):
    end_bucket = now.replace(minute=0, second=0, microsecond=0)
    buckets = [end_bucket - timedelta(hours=index) for index in range(hours - 1, -1, -1)]
    return buckets, {bucket: 0 for bucket in buckets}


def build_flows_over_time(flow_query, now):
    buckets, values = build_hourly_bucket_map(now, hours=24)
    since = buckets[0]

    rows = (
        flow_query
        .filter(FlowRegistry.created_at >= since)
        .with_entities(
            func.date_trunc("hour", FlowRegistry.created_at).label("bucket"),
            func.count(func.distinct(FlowRegistry.flow_id)).label("count"),
        )
        .group_by("bucket")
        .order_by("bucket")
        .all()
    )

    for row in rows:
        if row.bucket in values:
            values[row.bucket] = int(row.count)

    return [
        {
            "time": bucket.strftime("%H:%M"),
            "count": values[bucket],
        }
        for bucket in buckets
    ]


def build_classified_vs_routed(prediction_query, now):
    buckets, classified_values = build_hourly_bucket_map(now, hours=24)
    _, routed_values = build_hourly_bucket_map(now, hours=24)
    since = buckets[0]

    rows = (
        prediction_query
        .filter(PredictionResult.created_at >= since)
        .with_entities(
            func.date_trunc("hour", PredictionResult.created_at).label("bucket"),
            func.sum(case((PredictionResult.action == 0, 1), else_=0)).label("classified"),
            func.sum(case((PredictionResult.action == 1, 1), else_=0)).label("routed"),
        )
        .group_by("bucket")
        .order_by("bucket")
        .all()
    )

    for row in rows:
        if row.bucket in classified_values:
            classified_values[row.bucket] = int(row.classified or 0)
            routed_values[row.bucket] = int(row.routed or 0)

    return [
        {
            "time": bucket.strftime("%H:%M"),
            "classified": classified_values[bucket],
            "routed": routed_values[bucket],
        }
        for bucket in buckets
    ]


def build_traffic_mix(prediction_query):
    rows = (
        prediction_query
        .with_entities(
            PredictionResult.predicted_class.label("label"),
            func.count(PredictionResult.id).label("count"),
        )
        .group_by(PredictionResult.predicted_class)
        .order_by(func.count(PredictionResult.id).desc())
        .all()
    )

    total = sum(int(row.count or 0) for row in rows)

    return [
        {
            "label": str(row.label),
            "count": int(row.count or 0),
            "percent": round((float(row.count) / float(total) * 100.0) if total > 0 else 0.0, 2),
        }
        for row in rows
        if row.label is not None
    ]


def build_confidence_distribution(prediction_query):
    confidence_bin = case(
        (PredictionResult.max_p < 0.1, "0.0-0.1"),
        (PredictionResult.max_p < 0.2, "0.1-0.2"),
        (PredictionResult.max_p < 0.3, "0.2-0.3"),
        (PredictionResult.max_p < 0.4, "0.3-0.4"),
        (PredictionResult.max_p < 0.5, "0.4-0.5"),
        (PredictionResult.max_p < 0.6, "0.5-0.6"),
        (PredictionResult.max_p < 0.7, "0.6-0.7"),
        (PredictionResult.max_p < 0.8, "0.7-0.8"),
        (PredictionResult.max_p < 0.9, "0.8-0.9"),
        else_="0.9-1.0",
    ).label("confidence_bin")

    rows = (
        prediction_query
        .with_entities(
            confidence_bin,
            func.count(PredictionResult.id).label("count"),
        )
        .group_by(confidence_bin)
        .all()
    )

    value_map = {
        "0.0-0.1": 0,
        "0.1-0.2": 0,
        "0.2-0.3": 0,
        "0.3-0.4": 0,
        "0.4-0.5": 0,
        "0.5-0.6": 0,
        "0.6-0.7": 0,
        "0.7-0.8": 0,
        "0.8-0.9": 0,
        "0.9-1.0": 0,
    }

    for row in rows:
        value_map[str(row.confidence_bin)] = int(row.count or 0)

    return [
        {"range": key, "count": value_map[key]}
        for key in value_map
    ]


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


@router.get("/overview")
def get_dashboard_overview(request: Request, db: Session = Depends(get_db)):
    controller = get_controller(request)
    settings_manager = get_settings_manager_from_request(request)

    runtime_config = settings_manager.get_runtime_config()
    pipeline_name = runtime_config["flow_daemon"].get("feature_pipeline")

    now = utc_now()

    flow_query = build_flow_query(db, pipeline_name)
    prediction_query = build_prediction_query(db, pipeline_name)
    stats_model, stats_query = build_stats_query(db, pipeline_name)

    first_flow_created_at = flow_query.with_entities(func.min(FlowRegistry.created_at)).scalar()
    unique_flows = int(
        flow_query.with_entities(func.count(func.distinct(FlowRegistry.flow_id))).scalar() or 0
    )

    prediction_total = int(
        prediction_query.with_entities(func.count(PredictionResult.id)).scalar() or 0
    )

    classified_total = int(
        prediction_query
        .filter(PredictionResult.action == 0)
        .with_entities(func.count(PredictionResult.id))
        .scalar()
        or 0
    )

    routed_total = int(
        prediction_query
        .filter(PredictionResult.action == 1)
        .with_entities(func.count(PredictionResult.id))
        .scalar()
        or 0
    )

    classified_percent = (
        float(classified_total) / float(prediction_total) * 100.0
        if prediction_total > 0
        else 0.0
    )

    routed_percent = (
        float(routed_total) / float(prediction_total) * 100.0
        if prediction_total > 0
        else 0.0
    )

    predictions_per_min = float(
        prediction_query
        .filter(PredictionResult.created_at >= now - timedelta(minutes=1))
        .with_entities(func.count(PredictionResult.id))
        .scalar()
        or 0
    )

    low_confidence_count = int(
        prediction_query
        .filter(PredictionResult.max_p < LOW_CONFIDENCE_THRESHOLD)
        .with_entities(func.count(PredictionResult.id))
        .scalar()
        or 0
    )

    low_confidence_rate = (
        float(low_confidence_count) / float(prediction_total) * 100.0
        if prediction_total > 0
        else 0.0
    )

    processed_per_min = 0.0
    if stats_model is not None and stats_query is not None:
        processed_per_min = float(
            stats_query
            .filter(stats_model.created_at >= now - timedelta(minutes=1))
            .with_entities(func.count())
            .scalar()
            or 0
        )

    uptime_sec = (
        float((now - first_flow_created_at).total_seconds())
        if first_flow_created_at is not None
        else None
    )

    queue_size = controller.get_prediction_queue_count()

    return {
        "status": "running" if controller.is_running else "stopped",
        "is_running": controller.is_running,
        "pipeline_name": pipeline_name,
        "summary": {
            "uptime_sec": uptime_sec,
            "unique_flows": unique_flows,
            "processed_per_min": processed_per_min,
            "predictions_per_min": predictions_per_min,
            "prediction_total": prediction_total,
            "classified_total": classified_total,
            "classified_percent": round(classified_percent, 2),
            "routed_total": routed_total,
            "routed_percent": round(routed_percent, 2),
            "queue_size": queue_size,
            "low_confidence_count": low_confidence_count,
            "low_confidence_rate": round(low_confidence_rate, 2),
        },
        "charts": {
            "flows_over_time": build_flows_over_time(flow_query, now),
            "classified_vs_routed": build_classified_vs_routed(prediction_query, now),
            "traffic_mix": build_traffic_mix(prediction_query),
            "confidence_distribution": build_confidence_distribution(prediction_query),
        },
        "alerts": build_active_alerts(prediction_query, queue_size, now),
    }
