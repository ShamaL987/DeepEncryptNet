from __future__ import annotations
from typing import Dict, Any
import pandas as pd
from app.pipeline.helpers import infer_one
from app.pipeline.loader import get_flow_features_df
from app.database.db import session_scope
from app.database.models import PredictionResult


def _to_list(x):
    try:
        import numpy as np
        if isinstance(x, np.ndarray):
            return x.tolist()
    except Exception:
        pass
    return x


def hybrid_pipeline(flow_id: str) -> Dict[str, Any]:
    """Fetches features, predicts using DeepEncryptNet, and saves results."""

    df = get_flow_features_df(flow_id)
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame([df])

    out = infer_one(df)

    predicted_class = str(out.get("pred_label", ""))
    pred_idx = int(out.get("pred_idx", -1))
    action_val = int(out.get("action", 1))
    max_p = float(out.get("max_p", 0.0))
    margin = float(out.get("margin", 0.0))
    entropy = float(out.get("entropy", 0.0))
    probs_list = _to_list(out.get("probs"))
    embed_list = _to_list(out.get("embedding"))

    with session_scope() as db:
        existing = db.query(PredictionResult).filter(PredictionResult.flow_id == flow_id).first()

        if existing:
            return existing.prediction_result

        record = PredictionResult(
            flow_id=flow_id,
            pred_idx=pred_idx,
            predicted_class=predicted_class,
            action=action_val,
            max_p=max_p,
            margin=margin,
            entropy=entropy,
            probs=probs_list,
            embedding=embed_list,
            model_version=out.get("model_version"),
            manifest_path=out.get("manifest_path"),
        )
        record.save(db)

    return {
        "flow_id": flow_id,
        "predicted_class": predicted_class,
        "confidence": max_p,
        "action": action_val,
        "margin": margin,
        "entropy": entropy,
    }
