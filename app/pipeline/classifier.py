import numpy as np
import pandas as pd

from app.pipeline.helpers import predict_flow


def predict_random_flow(raw_df: pd.DataFrame, index: int | None = None):

    drop_cols = [c for c in ["class1", "win_seconds", "source_file"] if c in raw_df.columns]
    df_clean = raw_df.drop(columns=drop_cols, errors="ignore")

    if index is None:
        index = np.random.randint(0, len(df_clean))
    row = df_clean.iloc[index]

    true_label = None
    if "class1" in raw_df.columns:
        val = raw_df.iloc[index]["class1"]
        true_label = val.decode() if isinstance(val, bytes) else val

    print(f"🎯 Selected row index: {index}")
    print(f"🧩 Input columns: {len(df_clean.columns)} features")

    result = predict_flow(row)

    print(f"\n✅ Prediction Result:")
    print(f"   Predicted Class: {result['class_label']}")
    if true_label is not None:
        print(f"   True Class:      {true_label}")
    print(f"   Confidence:      {result['confidence']:.4f}")
    print(f"   Decision:        {result['decision'].upper()}")

    return result
