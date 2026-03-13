from __future__ import annotations

import pandas as pd

from app.database.db import session_scope
from app.database.models import HTTPSFlowStats
from app.pipeline.HTTPS.Initializer import HTTPSInference


def get_flow_features_df(flow_id: str, pipeline: HTTPSInference) -> pd.DataFrame:
    with session_scope() as db:
        row = db.query(HTTPSFlowStats).filter(HTTPSFlowStats.flow_id == flow_id).first()
        if not row:
            raise ValueError(f"No record found for flow_id: {flow_id}")

        data = {key: getattr(row, key, 0.0) for key in pipeline.kept_features}
        df = pd.DataFrame([data], columns=pipeline.kept_features)

    return df