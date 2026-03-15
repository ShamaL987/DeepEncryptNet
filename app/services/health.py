from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from app.database.models.flow_registry import FlowRegistry
from app.database.models.prediction_results import PredictionResult


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def average_or_none(values: list[float]) -> float | None:
    return float(mean(values)) if values else None


def percentile_95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1)))))
    return float(ordered[index])


def lag_ms_from_now(timestamp: datetime | None) -> float | None:
    if timestamp is None:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return float((utc_now() - timestamp).total_seconds() * 1000.0)


def calculate_pipeline_health_metrics(
    db: Session,
    pipeline_name: str | None = None,
    window_seconds: int = 60,
) -> dict[str, Any]:
    now = utc_now()
    window_start = now - timedelta(seconds=window_seconds)

    flow_query = db.query(FlowRegistry)
    prediction_query = db.query(PredictionResult)

    if pipeline_name:
        flow_query = flow_query.filter(FlowRegistry.pipeline_name == pipeline_name)
        prediction_query = (
            prediction_query
            .join(FlowRegistry, PredictionResult.flow_id == FlowRegistry.flow_id)
            .filter(FlowRegistry.pipeline_name == pipeline_name)
        )

    recent_flow_count = (
        flow_query
        .filter(FlowRegistry.created_at >= window_start)
        .count()
    )

    recent_prediction_count = (
        prediction_query
        .filter(PredictionResult.created_at >= window_start)
        .count()
    )

    latest_flow = (
        flow_query
        .order_by(FlowRegistry.created_at.desc())
        .first()
    )

    latest_prediction = (
        prediction_query
        .order_by(PredictionResult.created_at.desc())
        .first()
    )

    lag_query = (
        db.query(
            FlowRegistry.created_at.label("flow_created_at"),
            PredictionResult.created_at.label("prediction_created_at"),
        )
        .join(PredictionResult, PredictionResult.flow_id == FlowRegistry.flow_id)
    )

    if pipeline_name:
        lag_query = lag_query.filter(FlowRegistry.pipeline_name == pipeline_name)

    lag_rows = lag_query.all()

    flow_to_prediction_lags_ms = [
        float((row.prediction_created_at - row.flow_created_at).total_seconds() * 1000.0)
        for row in lag_rows
        if row.flow_created_at is not None and row.prediction_created_at is not None
    ]

    recent_prediction_rows = (
        prediction_query
        .filter(PredictionResult.created_at >= window_start)
        .with_entities(
            PredictionResult.max_p,
            PredictionResult.margin,
            PredictionResult.entropy,
            PredictionResult.action,
        )
        .all()
    )

    confidence_values = [float(row.max_p) for row in recent_prediction_rows if row.max_p is not None]
    margin_values = [float(row.margin) for row in recent_prediction_rows if row.margin is not None]
    entropy_values = [float(row.entropy) for row in recent_prediction_rows if row.entropy is not None]

    accepted_count = sum(1 for row in recent_prediction_rows if int(row.action) == 0)
    routed_count = sum(1 for row in recent_prediction_rows if int(row.action) == 1)
    total_prediction_rows = len(recent_prediction_rows)

    return {
        "flows_per_sec": float(recent_flow_count) / float(window_seconds),
        "predictions_per_sec": float(recent_prediction_count) / float(window_seconds),
        "latest_flow_lag_ms": lag_ms_from_now(latest_flow.created_at if latest_flow else None),
        "latest_prediction_lag_ms": lag_ms_from_now(latest_prediction.created_at if latest_prediction else None),
        "flow_to_prediction_lag_avg_ms": average_or_none(flow_to_prediction_lags_ms),
        "flow_to_prediction_lag_p95_ms": percentile_95(flow_to_prediction_lags_ms),
        "confidence_avg": average_or_none(confidence_values),
        "confidence_p95": percentile_95(confidence_values),
        "margin_avg": average_or_none(margin_values),
        "margin_p95": percentile_95(margin_values),
        "entropy_avg": average_or_none(entropy_values),
        "entropy_p95": percentile_95(entropy_values),
        "accepted_count": accepted_count,
        "routed_count": routed_count,
        "routed_percent": (
            float(routed_count) / float(total_prediction_rows) * 100.0
            if total_prediction_rows > 0
            else 0.0
        ),
    }