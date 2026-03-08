import json
from pathlib import Path
from typing import Union, Dict, Any, List

import numpy as np
import pandas as pd


def _as_path(p: Union[str, Path]) -> Path:
    return p if isinstance(p, Path) else Path(p)


def _read_json(fp: Path) -> Dict[str, Any]:
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)


def _ensure_df(x: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]) -> pd.DataFrame:
    if isinstance(x, pd.DataFrame):
        return x.copy()
    if isinstance(x, dict):
        return pd.DataFrame([x])
    if isinstance(x, list):
        return pd.DataFrame(x)
    raise TypeError("Input must be a DataFrame, dict (single row), or list of dict rows.")


def _coerce_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.replace([np.inf, -np.inf], np.nan)
    return out


def _softmax_np(logits: np.ndarray) -> np.ndarray:
    z = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(z)
    return exp / exp.sum(axis=1, keepdims=True)


def _probs_to_state(probs: np.ndarray) -> np.ndarray:
    probs = np.asarray(probs, dtype=np.float32)
    conf = probs.max(axis=1, keepdims=True)

    if probs.shape[1] >= 2:
        top2 = np.partition(probs, -2, axis=1)[:, -2:]
        margin = (top2[:, 1] - top2[:, 0]).reshape(-1, 1).astype(np.float32)
    else:
        margin = np.zeros((len(probs), 1), dtype=np.float32)

    entropy = (-np.sum(probs * np.log(np.clip(probs, 1e-9, 1.0)), axis=1, keepdims=True)).astype(np.float32)
    return np.concatenate([probs, conf.astype(np.float32), entropy, margin], axis=1).astype(np.float32)


def resolve_bundle_dir(run_or_bundle_dir: Union[str, Path]) -> Path:
    root = _as_path(run_or_bundle_dir).resolve()
    if (root / "inference_bundle.json").exists():
        return root
    if (root / "bundle" / "inference_bundle.json").exists():
        return (root / "bundle").resolve()
    raise FileNotFoundError("Could not find inference_bundle.json in given path (or its /bundle subfolder).")
