from __future__ import annotations
from typing import Mapping, Any
from sqlalchemy.orm import Session
from .models import FlowMin, FlowStats

def insert_flow_min(db: Session, flow_id: str) -> None:
    """
    Insert minimal flow record (id + extracted_at default). Ignore if exists.
    """
    if db.get(FlowMin, flow_id) is None:
        db.add(FlowMin(flow_id=flow_id))
    # caller commits

def upsert_flow_stats(db: Session, flow_id: str, stats: Mapping[str, Any]) -> None:
    """
    Insert/update stats for a given flow_id.
    """
    obj = db.get(FlowStats, flow_id)
    if obj is None:
        obj = FlowStats(flow_id=flow_id, **{k: stats.get(k) for k in stats.keys()})
        db.add(obj)
    else:
        for k, v in stats.items():
            setattr(obj, k, v)
    # caller commits
