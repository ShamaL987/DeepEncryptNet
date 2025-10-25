import numpy as np
import pandas as pd
import torch

from app.pipeline.classifier import get_logits
from app.pipeline.config import (
    train_feature_cols,
    shiftlog_params,
    imp,
    vt,
    corr_dropped,
    kept_features,
    std,
    robust,
    HARD_TAU,
    TAU,
    MARGIN,
    ROUTE_TAU,
    ROUTE_MARGIN,
    ROUTE_ENTROPY,
    HARD_GATE_AFTER_POLICY,
    DEVICE,
    model,
    temp,
    USE_POLICY,
    policy,
    classes
)


def _safe_div(a: pd.Series, b: pd.Series | float):
    out = a.astype(float) / float(b)
    return out.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def apply_shiftlog(X: pd.DataFrame, params: dict) -> pd.DataFrame:
    assert list(X.columns) == params["cols"], "ShiftLog columns mismatch."
    arr = X.values.astype(float) + np.array(params["shift"], dtype=float)
    mask = np.array(params["log_mask"], dtype=bool)
    if mask.any():
        # NEW: robust guard for adversarial/OO-range negatives
        arr[:, mask] = np.maximum(arr[:, mask], -0.999999)
        arr[:, mask] = np.log1p(arr[:, mask])
    out = pd.DataFrame(arr, columns=X.columns, index=X.index)
    return out.replace([np.inf, -np.inf], np.nan)


def preprocess_row_df(x_df_raw: pd.DataFrame) -> np.ndarray:
    x_df = x_df_raw.reindex(columns=train_feature_cols)
    if x_df.isnull().any().any():
        x_df = x_df.fillna(0.0)
    x_sl = apply_shiftlog(x_df, shiftlog_params)
    x_imp = pd.DataFrame(imp.transform(x_sl), columns=x_sl.columns, index=x_sl.index)
    cols_after_vt = [train_feature_cols[i] for i in vt.get_support(indices=True)]
    x_vt = x_imp[cols_after_vt].copy()
    x_corr = x_vt.drop(columns=corr_dropped, errors="ignore").reindex(columns=kept_features)
    x_sc = std.transform(robust.transform(x_corr.values))
    return x_sc


@torch.no_grad()
def build_state_from_logits(logits):
    probs = torch.softmax(logits, dim=1)
    top2 = torch.topk(probs, k=2, dim=1).values
    max_p = top2[:, :1]
    margin = (top2[:, 0] - top2[:, 1]).unsqueeze(1)
    ent = -(probs * (probs.clamp_min(1e-9)).log()).sum(dim=1, keepdim=True)
    state = torch.cat([probs, max_p, ent, margin], dim=1)
    return state, probs, max_p, ent, margin


@torch.no_grad()
def apply_gate(probs, ent, action):
    top2 = torch.topk(probs, k=2, dim=1).values
    m_p = top2[:, 0]
    m_g = (top2[:, 0] - top2[:, 1]).clamp_min_(0)
    hard_accept = (m_p >= HARD_TAU)
    accept = (m_p >= TAU) & (m_g >= MARGIN)
    must_route = (m_p < ROUTE_TAU) | (m_g < ROUTE_MARGIN) | (ent.squeeze(1) > ROUTE_ENTROPY)
    if HARD_GATE_AFTER_POLICY:
        action = torch.where(must_route, torch.ones_like(action), action)
        action = torch.where(accept, torch.zeros_like(action), action)
        action = torch.where(hard_accept, torch.zeros_like(action), action)
    else:
        action = torch.where(hard_accept, torch.zeros_like(action), action)
        action = torch.where(accept, torch.zeros_like(action), action)
        action = torch.where(must_route, torch.ones_like(action), action)
    return action, m_p, m_g


@torch.no_grad()
def infer_one(feature_row_df: pd.DataFrame):
    X = preprocess_row_df(feature_row_df)
    xb = torch.from_numpy(X.astype(np.float32)).unsqueeze(1).to(DEVICE)
    out = model(xb)
    logits = temp(get_logits(out))
    state, probs, max_p, ent, margin = build_state_from_logits(logits)
    if USE_POLICY:
        logpi = policy(state)
        action = torch.argmax(logpi, dim=1)
    else:
        action = torch.ones((xb.size(0),), dtype=torch.long, device=DEVICE)
    action, m_p, m_g = apply_gate(probs, ent, action)
    idx = int(probs.argmax(1)[0].item())
    return {
        "pred_idx": idx,
        "pred_label": str(classes[idx]),
        "action": int(action[0].item()),
        "max_p": float(m_p[0].item()),
        "margin": float(m_g[0].item()),
        "entropy": float(ent[0].item()),
        "probs": probs[0].detach().cpu().numpy(),
        "embedding": out[1][0].detach().cpu().numpy() if isinstance(out, (tuple, list)) else None
    }
