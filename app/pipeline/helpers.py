import os, json, joblib, torch, random
import numpy as np, pandas as pd
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from typing import Union
from sklearn.preprocessing import StandardScaler
from collections import Counter

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


ROOT = Path("app/pipeline/deepv4")
MANIFEST_PATH = ROOT / "logs" / "artifacts_manifest.json"

with open(MANIFEST_PATH, "r") as f:
    manifest = json.load(f)

A = manifest["artifacts"]
RUNTIME = manifest.get("runtime", {})
MODEL_CFG = manifest.get("model_config", {})
RATIO_NORM_PARAMS = manifest.get("ratio_norm_params", None)

class FeatureCNN_Attn(nn.Module):
    def __init__(self, n_feats, n_classes, drop=0.35, return_embedding=True):
        super().__init__()
        self.return_embedding = return_embedding
        self.conv1 = nn.Conv1d(1, 128, 5, padding=2)
        self.bn1   = nn.BatchNorm1d(128)
        self.conv2 = nn.Conv1d(128, 256, 3, padding=1)
        self.bn2   = nn.BatchNorm1d(256)
        self.attn  = nn.MultiheadAttention(embed_dim=256, num_heads=4, dropout=drop, batch_first=True)
        self.ln    = nn.LayerNorm(256)
        self.head  = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(drop),
        )
        self.out   = nn.Linear(128, n_classes)

    def forward(self, x):          # x: (B,1,F)
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))   # (B,256,F)
        x = x.transpose(1, 2)                 # (B,F,256)
        attn_out, _ = self.attn(x, x, x)
        x = self.ln(x + attn_out)             # residual + norm
        x = x.mean(dim=1)                     # (B,256)
        emb = self.head(x)                    # (B,128)
        logits = self.out(emb)                # (B,C)
        return (logits, emb) if self.return_embedding else logits

class TemperatureScaler(nn.Module):
    def __init__(self):
        super().__init__()
        self.log_t = nn.Parameter(torch.zeros(1))
    def forward(self, logits):
        return logits / torch.exp(self.log_t)

class RLDecisionLayer(nn.Module):
    def __init__(self, in_dim, hidden=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, 2)  # 0=CLASSIFY, 1=ROUTE
        )
    def forward(self, s):
        return F.log_softmax(self.net(s), dim=-1)

def get_logits(model_out):
    return model_out[0] if isinstance(model_out, (tuple, list)) else model_out



shiftlog_params = joblib.load(ROOT / A["shiftlog_params"])
imp   = joblib.load(ROOT / A["imputer"])
vt    = joblib.load(ROOT / A["variance_threshold"])
robust= joblib.load(ROOT / A["robust_scaler"])
std   = joblib.load(ROOT / A["standard_scaler"])
kept_features      = json.load(open(ROOT / A["kept_features"]))
corr_dropped       = json.load(open(ROOT / A["corr_dropped"]))
train_feature_cols = json.load(open(ROOT / A["train_feature_cols"]))
classes            = np.load(ROOT / A["label_classes"], allow_pickle=True)

n_feats   = int(MODEL_CFG.get("n_feats", len(kept_features)))
n_classes = int(MODEL_CFG.get("n_classes", len(classes)))

model = FeatureCNN_Attn(n_feats=n_feats, n_classes=n_classes, drop=MODEL_CFG.get("dropout", 0.35)).to(DEVICE)
model.load_state_dict(torch.load(ROOT / A["cnn_state_dict"], map_location=DEVICE))
model.eval()

temp = TemperatureScaler().to(DEVICE)
temp.load_state_dict(torch.load(ROOT / A["temp_state_dict"], map_location=DEVICE))
temp.eval()

policy = RLDecisionLayer(in_dim=n_classes+3, hidden=32).to(DEVICE)
policy.load_state_dict(torch.load(ROOT / A["rl_policy"], map_location=DEVICE))
policy.eval()

# ---------- Runtime thresholds ----------
TAU       = float(RUNTIME.get("accept_thresholds", {}).get("TAU", 0.88))
HARD_TAU  = float(RUNTIME.get("accept_thresholds", {}).get("HARD_TAU", 0.95))
MARGIN    = float(RUNTIME.get("accept_thresholds", {}).get("MARGIN", 0.05))
USE_POLICY= bool(RUNTIME.get("use_policy", True))

# Route thresholds
ROUTE_TAU      = float(RUNTIME.get("route_thresholds", {}).get("ROUTE_TAU", 0.65))
ROUTE_MARGIN   = float(RUNTIME.get("route_thresholds", {}).get("ROUTE_MARGIN", 0.12))
ROUTE_ENTROPY  = float(RUNTIME.get("route_thresholds", {}).get("ROUTE_ENTROPY", 1.00))


def _safe_div(a, b):
    """Safe element-wise division handling scalar, Series, and dict types."""
    # Resolve b to a float (handles dicts, Series, arrays, etc.)
    if isinstance(b, (pd.Series, np.ndarray)) and len(b) == 1:
        b = float(b.iloc[0] if isinstance(b, pd.Series) else b[0])
    elif isinstance(b, dict):
        b = float(b.get("mean", 1.0))
    elif not np.isscalar(b):
        try:
            b = float(np.mean(b))
        except Exception:
            b = 1.0
    else:
        b = float(b)

    out = a.astype(float) / b
    return out.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def apply_ratio_normalization(df: pd.DataFrame, params: dict | None) -> pd.DataFrame:
    """Apply the exact ratio-norm used during training (no-op if params=None)."""
    if not params:
        return df.copy()

    out = df.copy()
    dur_ref = params["dur_ref"]
    pps_ref = params["pps_ref"]
    bps_ref = params["bps_ref"]

    # scaling factors
    dur_scale = _safe_div(out["duration"], dur_ref) if "duration" in out else pd.Series(1.0, index=out.index)
    pps_scale = _safe_div(out["flowPktsPerSecond"], pps_ref) if "flowPktsPerSecond" in out else pd.Series(1.0, index=out.index)

    # time-like columns normalized by duration
    time_cols = [
        "duration","max_active",
        "max_biat","max_fiat","max_flowiat",
        "mean_biat","mean_fiat","mean_flowiat",
        "min_biat","min_fiat","min_flowiat",
        "std_active","std_flowiat",
        "total_biat","total_fiat",
    ]
    for c in time_cols:
        if c in out.columns:
            out[c] = _safe_div(out[c], dur_scale)

    # IAT-related columns also scale w.r.t PPS
    iat_cols = [
        "max_biat","max_fiat","max_flowiat",
        "mean_biat","mean_fiat","mean_flowiat",
        "min_biat","min_fiat","min_flowiat",
        "std_flowiat","total_biat","total_fiat",
    ]
    for c in iat_cols:
        if c in out.columns:
            out[c] = out[c] * pps_scale

    # rates → ratios
    if "flowPktsPerSecond" in out.columns:
        out["flowPktsPerSecond"] = _safe_div(out["flowPktsPerSecond"], pps_ref)
    if "flowBytesPerSecond" in out.columns:
        out["flowBytesPerSecond"] = _safe_div(out["flowBytesPerSecond"], bps_ref)

    return out

# ---------- Preprocess utilities ----------
def apply_shiftlog(X: pd.DataFrame, params: dict) -> pd.DataFrame:
    assert list(X.columns) == params["cols"], "ShiftLog columns mismatch."
    arr = X.values.astype(float) + np.array(params["shift"], dtype=float)
    mask = np.array(params["log_mask"], dtype=bool)
    if mask.any():
        arr[:, mask] = np.maximum(arr[:, mask], -0.999999)
        arr[:, mask] = np.log1p(arr[:, mask])
    out = pd.DataFrame(arr, columns=X.columns, index=X.index)
    return out.replace([np.inf, -np.inf], np.nan)

def preprocess_row_df(x_df_raw: pd.DataFrame) -> np.ndarray:
    # 0) ratio normalization FIRST (keeps parity with training)
    x_df_rn = apply_ratio_normalization(x_df_raw, RATIO_NORM_PARAMS)

    # 1) column align to training order (add any missing as 0.0)
    x_df = x_df_rn.reindex(columns=train_feature_cols)
    if x_df.isnull().any().any():
        x_df = x_df.fillna(0.0)

    # 2) Shift+Log transform
    x_sl = apply_shiftlog(x_df, shiftlog_params)

    # 3) Impute (median)
    x_imp = pd.DataFrame(imp.transform(x_sl), columns=x_sl.columns, index=x_sl.index)

    # 4) Variance threshold feature selection
    cols_after_vt = [train_feature_cols[i] for i in vt.get_support(indices=True)]
    x_vt = x_imp[cols_after_vt].copy()

    # 5) Drop correlated features to match kept_features
    x_corr = x_vt.drop(columns=corr_dropped, errors="ignore").reindex(columns=kept_features)

    # 6) Robust -> Standard scaling (same order used in training)
    x_sc = std.transform(robust.transform(x_corr.values))
    return x_sc

@torch.no_grad()
def build_state_from_logits(logits: torch.Tensor):
    probs  = torch.softmax(logits, dim=1)
    top2   = torch.topk(probs, k=2, dim=1).values
    max_p  = top2[:, :1]
    margin = (top2[:,0] - top2[:,1]).unsqueeze(1)
    ent    = - (probs * (probs.clamp_min(1e-9)).log()).sum(dim=1, keepdim=True)
    state  = torch.cat([probs, max_p, ent, margin], dim=1)
    return state, probs, max_p, ent, margin

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
        action = torch.ones((1,), dtype=torch.long, device=DEVICE)

    # Routing
    top2 = torch.topk(probs, k=2, dim=1).values
    m_p = top2[:,0]
    m_g = (top2[:,0] - top2[:,1])

    route_mask = (m_p < ROUTE_TAU) | (m_g < ROUTE_MARGIN) | (ent.squeeze(1) > ROUTE_ENTROPY)
    action[route_mask] = 1

    # Accept if confident
    action[(m_p >= TAU) & (m_g >= MARGIN)] = 0
    action[m_p >= HARD_TAU] = 0

    pred_idx = int(probs.argmax(1).item())
    return {
        "pred_idx": pred_idx,
        "pred_label": str(classes[pred_idx]),
        "action": int(action.item()),
        "max_p": float(m_p.item()),
        "margin": float(m_g.item()),
        "entropy": float(ent.item()),
        "probs": probs.squeeze(0).cpu().numpy(),
        "embedding": out[1].squeeze(0).cpu().numpy() if isinstance(out, (tuple, list)) else None,
    }

def predict_one(df: pd.DataFrame):

    out = infer_one(df)
    return out

