from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.db import get_db
from app.database.models import FlowStats, PredictionResult

router = APIRouter(prefix="/api", tags=["dashboard"])



@router.get("/status")
def system_status(db: Session = Depends(get_db)):
    first_start = db.query(func.min(FlowStats.start_time)).scalar()
    last_pred = db.query(func.max(PredictionResult.created_at)).scalar()
    total_flows = db.query(FlowStats).count()

    now = datetime.now(timezone.utc).timestamp()
    uptime = now - first_start if first_start else None

    return {
        "running": True,
        "uptime_sec": uptime,
        "flows_processed": total_flows,
        "last_update": last_pred
    }

@router.get("/analytics/classes")
def class_distribution(
    window_sec: int = Query(60, ge=10, le=3600),
    db: Session = Depends(get_db)
):
    since = datetime.now(timezone.utc) - timedelta(seconds=window_sec)

    rows = (
        db.query(
            PredictionResult.predicted_class,
            func.count(PredictionResult.id)
        )
        .filter(PredictionResult.created_at >= since)
        .group_by(PredictionResult.predicted_class)
        .all()
    )

    dist = {cls: cnt for cls, cnt in rows}

    return {
        "window_sec": window_sec,
        "total": sum(dist.values()),
        "distribution": dist
    }

@router.get("/analytics/routing")
def routing_summary(
    window_sec: int = Query(60, ge=10, le=3600),
    db: Session = Depends(get_db)
):
    since = datetime.now(timezone.utc) - timedelta(seconds=window_sec)

    classified = (
        db.query(PredictionResult)
        .filter(
            PredictionResult.created_at >= since,
            PredictionResult.action == 0
        )
        .count()
    )

    routed = (
        db.query(PredictionResult)
        .filter(
            PredictionResult.created_at >= since,
            PredictionResult.action == 1
        )
        .count()
    )

    total = classified + routed

    return {
        "window_sec": window_sec,
        "classified": classified,
        "routed": routed,
        "route_rate": routed / total if total else 0.0
    }


@router.get("/analytics/classified")
def classified_only(
    window_sec: int = Query(60, ge=10, le=3600),
    db: Session = Depends(get_db)
):
    since = datetime.now(timezone.utc) - timedelta(seconds=window_sec)

    rows = (
        db.query(
            PredictionResult.predicted_class,
            func.count(PredictionResult.id)
        )
        .filter(
            PredictionResult.created_at >= since,
            PredictionResult.action == 0
        )
        .group_by(PredictionResult.predicted_class)
        .all()
    )

    return {
        "window_sec": window_sec,
        "distribution": {cls: cnt for cls, cnt in rows}
    }


@router.get("/analytics/routed")
def routed_only(
    window_sec: int = Query(60, ge=10, le=3600),
    db: Session = Depends(get_db)
):
    since = datetime.now(timezone.utc) - timedelta(seconds=window_sec)

    rows = (
        db.query(
            PredictionResult.predicted_class,
            func.count(PredictionResult.id)
        )
        .filter(
            PredictionResult.created_at >= since,
            PredictionResult.action == 1
        )
        .group_by(PredictionResult.predicted_class)
        .all()
    )

    return {
        "window_sec": window_sec,
        "distribution": {cls: cnt for cls, cnt in rows}
    }

@router.get("/analytics/confidence")
def confidence_entropy(
    window_sec: int = Query(60, ge=10, le=3600),
    db: Session = Depends(get_db)
):
    since = datetime.now(timezone.utc) - timedelta(seconds=window_sec)

    avg_conf, avg_ent = (
        db.query(
            func.avg(PredictionResult.max_p),
            func.avg(PredictionResult.entropy)
        )
        .filter(PredictionResult.created_at >= since)
        .one()
    )

    return {
        "window_sec": window_sec,
        "avg_confidence": float(avg_conf) if avg_conf else None,
        "avg_entropy": float(avg_ent) if avg_ent else None
    }
@router.get("/flows/recent")
def recent_flows(
    limit: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db)
):
    rows = (
        db.query(
            FlowStats.flow_id,
            FlowStats.start_time,
            FlowStats.end_time,
            FlowStats.duration,
            FlowStats.flowBytesPerSecond,
            PredictionResult.predicted_class,
            PredictionResult.action,
            PredictionResult.max_p,
            PredictionResult.entropy,
            PredictionResult.created_at
        )
        .join(PredictionResult, FlowStats.flow_id == PredictionResult.flow_id)
        .order_by(PredictionResult.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "flow_id": r.flow_id,
            "start_ts": r.start_time,
            "end_ts": r.end_time,
            "duration_sec": r.duration,
            "size_bytes": r.flowBytesPerSecond * r.duration,
            "predicted_class": r.predicted_class,
            "action": "ROUTE" if r.action == 1 else "CLASSIFY",
            "confidence": r.max_p,
            "entropy": r.entropy,
            "created_at": r.created_at
        }
        for r in rows
    ]
