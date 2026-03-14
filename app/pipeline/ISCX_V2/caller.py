from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from app.database.db import session_scope
from app.database.models import PredictionResult
from app.pipeline.ISCX_V2.Initializer import ISCXV2Inference
from app.pipeline.ISCX_V2.loader import get_flow_features_df




def _record_to_result(record: PredictionResult) -> dict[str, Any]:
    return {
        "flow_id": record.flow_id,
        "predicted_class": record.predicted_class,
        "confidence": record.max_p,
        "action": record.action,
        "margin": record.margin,
        "entropy": record.entropy,
    }


def _choose_action(row: pd.Series) -> int:
    if "action_rl" in row and pd.notna(row["action_rl"]):
        return int(row["action_rl"])
    if "action_threshold" in row and pd.notna(row["action_threshold"]):
        return int(row["action_threshold"])
    return 1


def _extract_probs(row: pd.Series) -> list[float]:
    prob_cols = [col for col in row.index if str(col).startswith("p_")]
    return [float(row[col]) for col in prob_cols]


def _extract_embedding(row: pd.Series) -> list[float] | None:
    emb_cols = [col for col in row.index if str(col).startswith("emb_")]
    if not emb_cols:
        return None
    return [float(row[col]) for col in emb_cols]


def hybrid_pipeline(flow_id: str, pipeline: ISCXV2Inference) -> Dict[str, Any]:
    df = get_flow_features_df(flow_id, pipeline)
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame([df])


    out_df = pipeline.predict(
        df,
        return_probs=True,
        return_embeddings=True,
    )

    row = out_df.iloc[0]

    predicted_class = str(row["pred_class"])
    pred_idx = int(row["pred_class_id"])
    action_val = _choose_action(row)
    max_p = float(row["confidence"])
    margin = float(row["top2_margin"])
    entropy = float(row["entropy"])
    probs_list = _extract_probs(row)
    embed_list = _extract_embedding(row)

    with session_scope() as db:
        existing = db.query(PredictionResult).filter(PredictionResult.flow_id == flow_id).first()
        if existing:
            return _record_to_result(existing)

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
            model_version=row.get("model_version"),
            manifest_path=row.get("manifest_path"),
        )
        record.save(db)

    return {
        "flow_id": flow_id,
        "predicted_class": predicted_class,
        "confidence": max_p,
        "action": action_val,
        "margin": margin,
        "entropy": entropy,
        "pipeline_name": "ISCX_V2",
    }