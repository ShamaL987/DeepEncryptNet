import pandas as pd

from app.pipeline.HTTPS.Initializer import HTTPSInference

BUNDLE_DIR = r"v7/https_v1/bundle"

def run_predict(df_live: pd.DataFrame):


    pipeline = HTTPSInference(BUNDLE_DIR)
    kept = pipeline.kept_features


    for c in kept:
        if c not in df_live.columns:
            raise ValueError(f"CSV is missing required kept feature: {c}")
        df_live[c] = pd.to_numeric(df_live[c], errors="coerce")

    df_live = df_live[kept].copy()


    out = pipeline.predict(df_live, return_probs=False, return_embeddings=False)

    print(out)