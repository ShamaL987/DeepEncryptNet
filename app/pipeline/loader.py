from __future__ import annotations
from typing import Union
from pathlib import Path
import pandas as pd
import json

from app.database.db import session_scope
from app.database.models import FlowStats


KEPT_FEATURES_PATH = Path("app/pipeline/deepv8/kept_features.json")


def load_kept_features() -> list[str]:
    """Load kept feature names from JSON file."""
    with KEPT_FEATURES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_flow_features_df(flow_id: str) -> pd.DataFrame:
    """Fetch 17 flow features from DB, align with kept_features.json."""
    kept_features = load_kept_features()

    with session_scope() as db:
        row = db.query(FlowStats).filter(FlowStats.flow_id == flow_id).first()
        if not row:
            raise ValueError(f"No record found for flow_id: {flow_id}")

        data = {k: getattr(row, k, 0.0) for k in kept_features}
        df = pd.DataFrame([data], columns=kept_features)

    return df

