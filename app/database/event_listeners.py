from __future__ import annotations
import os
import logging
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import event
from sqlalchemy.orm import Session
from app.database.models import FlowStats
from app.pipeline.caller import hybrid_pipeline

_executor = ThreadPoolExecutor(max_workers=int(os.getenv("PREDICT_MAX_WORKERS", "2")))

@event.listens_for(Session, "after_flush")
def _collect_new_flowstats(session: Session, flush_context):
    """Collects newly added FlowStats ids during flush."""
    ids = session.info.setdefault("new_flowstats", set())
    ids.update(obj.flow_id for obj in session.new if isinstance(obj, FlowStats))

@event.listens_for(Session, "after_commit")
def _kickoff_predictions(session: Session):
    """Submits background predictions for committed FlowStats."""
    ids = session.info.pop("new_flowstats", None)
    if not ids:
        return
    for fid in ids:
        _executor.submit(_predict_worker, fid)

def _predict_worker(flow_id: str):
    """Runs hybrid prediction for a flow id."""
    try:
        res = hybrid_pipeline(flow_id)
        logging.info(f"[PREDICT] {flow_id} -> {res.get('predicted_class')} {res.get('confidence')}")
    except Exception as e:
        logging.exception(f"[PREDICT] failed for {flow_id}: {e}")

def shutdown_prediction_executor():
    """Shuts down the prediction executor."""
    _executor.shutdown(wait=False)
