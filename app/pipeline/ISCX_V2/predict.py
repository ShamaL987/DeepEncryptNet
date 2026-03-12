import pandas as pd

from app.pipeline.ISCX_V2.Initializer import ISCXV2Inference

BUNDLE_DIR = r"v5/v1/bundle"


def run_predict(df_live: pd.DataFrame):

    pipeline = ISCXV2Inference(BUNDLE_DIR)

    out = pipeline.predict(df_live, return_probs=False, return_embeddings=False)
    print(out)