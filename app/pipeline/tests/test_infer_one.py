import numpy as np
import pytest

from app.pipeline.test1 import infer_one
from app.pipeline.tests.test_data import make_valid_feature_df, VOIP_DATA, FT_DATA


def test_infer_one_returns_dict():
    df = make_valid_feature_df(FT_DATA[2])
    result = infer_one(df)

    assert isinstance(result, dict)
    print(result)


def test_infer_one_has_required_keys():
    df = make_valid_feature_df()
    result = infer_one(df)

    expected_keys = {
        "pred_idx",
        "pred_label",
        "action",
        "max_p",
        "margin",
        "entropy",
        "probs",
        "embedding",
    }

    assert expected_keys.issubset(result.keys())


def test_infer_one_prediction_index_valid():
    df = make_valid_feature_df()
    result = infer_one(df)

    assert isinstance(result["pred_idx"], int)
    assert result["pred_idx"] >= 0


def test_infer_one_probabilities_sum_to_one():
    df = make_valid_feature_df()
    result = infer_one(df)

    probs = result["probs"]
    assert isinstance(probs, np.ndarray)
    np.testing.assert_allclose(probs.sum(), 1.0, rtol=1e-5)


def test_infer_one_entropy_non_negative():
    df = make_valid_feature_df()
    result = infer_one(df)

    assert result["entropy"] >= 0.0


def test_infer_one_action_is_int():
    df = make_valid_feature_df()
    result = infer_one(df)

    assert isinstance(result["action"], int)


def test_infer_one_embedding_shape():
    df = make_valid_feature_df()
    result = infer_one(df)

    if result["embedding"] is not None:
        assert result["embedding"].ndim == 1
        assert result["embedding"].shape[0] > 0
