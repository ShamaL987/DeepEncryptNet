from __future__ import annotations
from typing import Dict, Any
import pandas as pd
from app.pipeline.helpers import predict_flow
from app.pipeline.loader import get_flow_features_df
from app.database.db import session_scope
from app.database.models import PredictionResult


def hybrid_pipeline(flow_id: str) -> Dict[str, Any]:
    """Fetches features, predicts using DeepEncryptNet, and saves results."""

    df = get_flow_features_df(flow_id)
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame([df])

    out = predict_flow(df)

    action_val = 0 if out.get("decision") == "accepted" else 1

    predicted_class = str(out.get("class_label", ""))
    max_p = float(out.get("confidence", 0.0))
    margin = float(out.get("margin", 0.0))
    entropy = float(out.get("entropy", 0.0))

    with session_scope() as db:
        existing = db.query(PredictionResult).filter(PredictionResult.flow_id == flow_id).first()

        if existing:
            existing.predicted_class = predicted_class
            existing.action = action_val
            existing.max_p = max_p
            existing.margin = margin
            existing.entropy = entropy
            existing.model_version = out.get("model_version")
            existing.manifest_path = out.get("manifest_path")
            existing.save(db)
        else:
            record = PredictionResult(
                flow_id=flow_id,
                predicted_class=predicted_class,
                action=action_val,
                max_p=max_p,
                margin=margin,
                entropy=entropy,
                model_version=out.get("model_version"),
                manifest_path=out.get("manifest_path"),
            )
            record.save(db)

    return {
        "flow_id": flow_id,
        "predicted_class": predicted_class,
        "confidence": max_p,
        "decision": out.get("decision"),
        "margin": margin,
        "entropy": entropy,
    }
