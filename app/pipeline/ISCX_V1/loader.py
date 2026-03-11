from __future__ import annotations
import pandas as pd

from app.database.db import session_scope
from app.database.models import FlowStats
from app.pipeline.ISCX_V1.config import kept_features


def get_flow_features_df(flow_id: str) -> pd.DataFrame:
    """Fetch 17 flow features from DB, align with kept_features.json."""

    with session_scope() as db:
        row = db.query(FlowStats).filter(FlowStats.flow_id == flow_id).first()
        if not row:
            raise ValueError(f"No record found for flow_id: {flow_id}")

        data = {k: getattr(row, k, 0.0) for k in kept_features}
        df = pd.DataFrame([data], columns=kept_features)

    return df

