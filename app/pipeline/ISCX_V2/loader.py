from __future__ import annotations

import pandas as pd

from app.database.db import session_scope
from app.database.models import ISCXFlowStatsV2
from app.pipeline.ISCX_V2.Initializer import ISCXV2Inference


def get_flow_features_df(flow_id: str, pipeline: ISCXV2Inference) -> pd.DataFrame:
    with session_scope() as db:
        row = db.query(ISCXFlowStatsV2).filter(ISCXFlowStatsV2.flow_id == flow_id).first()
        if not row:
            raise ValueError(f"No record found for flow_id: {flow_id}")

        data = {key: getattr(row, key, 0.0) for key in pipeline.kept_features}
        df = pd.DataFrame([data], columns=pipeline.kept_features)

    return df