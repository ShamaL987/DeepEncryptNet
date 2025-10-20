import os, json, joblib, torch, random
import numpy as np, pandas as pd
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from typing import Union
from sklearn.preprocessing import StandardScaler
from collections import Counter

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def set_seed(seed: int = 1234):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

set_seed(1234)


ROOT = Path("app/pipeline/deepv8")
MANIFEST_PATH = ROOT / "logs" / "artifacts_manifest.json"

with open(MANIFEST_PATH, "r") as f:
    manifest = json.load(f)

A = manifest["artifacts"]

shiftlog_params = joblib.load(ROOT / A["shiftlog_params"])
imputer         = joblib.load(ROOT / A["imputer"])
var_thresh      = joblib.load(ROOT / A["variance_threshold"])
robust_scaler   = joblib.load(ROOT / A["robust_scaler"])
std_scaler      = joblib.load(ROOT / A["standard_scaler"])
label_encoder   = joblib.load(ROOT / A["label_encoder"])
label_classes   = np.load(ROOT / A["label_classes"], allow_pickle=True)

train_feature_cols      = json.load(open(ROOT / A["train_feature_cols"]))
kept_features           = json.load(open(ROOT / A["kept_features"]))
train_cols_after_ratios = json.load(open(ROOT / A["train_feature_cols_after_ratios"]))

rl_cfg  = manifest["rl_config"]
rt_cfg  = manifest["runtime"]

TAU           = rt_cfg["accept_thresholds"]["TAU"]
HARD_TAU      = rt_cfg["accept_thresholds"]["HARD_TAU"]
MARGIN        = rt_cfg["accept_thresholds"]["MARGIN"]
ROUTE_TAU     = rt_cfg["route_thresholds"]["ROUTE_TAU"]
ROUTE_MARGIN  = rt_cfg["route_thresholds"]["ROUTE_MARGIN"]
ROUTE_ENTROPY = rt_cfg["route_thresholds"]["ROUTE_ENTROPY"]
USE_POLICY    = rt_cfg["use_policy"]


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
        self.head  = nn.Sequential(nn.Linear(256,128), nn.ReLU(inplace=True), nn.Dropout(drop))
        self.out   = nn.Linear(128, n_classes)
    def forward(self, x):
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = x.transpose(1,2)
        attn_out,_ = self.attn(x,x,x)
        x = self.ln(x + attn_out)
        x = x.mean(dim=1)
        emb = self.head(x)
        logits = self.out(emb)
        return (logits, emb)

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
            nn.Linear(in_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 2)  # 0=CLASSIFY, 1=ROUTE
        )
    def forward(self, s):
        return F.log_softmax(self.net(s), dim=-1)

def add_ratio_features_core(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    eps = 1e-9
    if "duration" not in df.columns:
        raise ValueError("‘duration’ required for ratio features.")
    dur = df["duration"].astype(float).clip(lower=eps)
    def safe_div(a, b): return a.astype(float) / b.astype(float).clip(lower=eps)
    for col in df.columns:
        if col != "duration":
            out[f"{col}_over_duration"] = safe_div(df[col], dur)
    if {"flowBytesPerSecond", "flowPktsPerSecond"} <= set(df.columns):
        out["bytes_per_packet"] = safe_div(df["flowBytesPerSecond"], df["flowPktsPerSecond"])
    else:
        out["bytes_per_packet"] = 0.0
    return out.replace([np.inf, -np.inf], 0.0).fillna(0.0)

def _to_1row_df(row_like):
    if isinstance(row_like, pd.Series): return row_like.to_frame().T
    if isinstance(row_like, dict): return pd.DataFrame([row_like])
    if isinstance(row_like, pd.DataFrame): return row_like.copy()
    raise TypeError("Input must be dict, Series, or DataFrame")

def _apply_shiftlog(df, params):
    df = df.reindex(columns=params["cols"])
    arr = df.values.astype(float)
    shift = np.array(params["shift"], dtype=float)
    log_mask = np.array(params["log_mask"], dtype=bool)
    arr = arr + shift
    arr[:, log_mask] = np.log1p(np.clip(arr[:, log_mask], a_min=0.0, a_max=None))
    return pd.DataFrame(arr, columns=params["cols"])

def preprocess_df(df_in: pd.DataFrame) -> pd.DataFrame:
    df = df_in.copy()
    df = df.reindex(columns=train_feature_cols)
    for c in df.columns:
        if df[c].dtype.kind not in "biufc":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.replace([np.inf, -np.inf], np.nan)
    X_sl = _apply_shiftlog(df, shiftlog_params)
    X_imp = pd.DataFrame(imputer.transform(X_sl), columns=X_sl.columns)
    X_vt = pd.DataFrame(var_thresh.transform(X_imp.values),
                        columns=[train_feature_cols[i] for i in var_thresh.get_support(indices=True)])
    X_corr = X_vt.reindex(columns=kept_features)
    X_rat = add_ratio_features_core(X_corr)
    X_rob = robust_scaler.transform(X_rat.values)
    X_std = std_scaler.transform(X_rob)
    X_fin = pd.DataFrame(X_std, columns=X_rat.columns)
    return X_fin.reindex(columns=train_cols_after_ratios).fillna(0.0)

def build_state_from_logits(logits):
    probs  = torch.softmax(logits, dim=1)
    top2   = torch.topk(probs, k=2, dim=1).values
    max_p  = top2[:, :1]
    margin = (top2[:,0] - top2[:,1]).unsqueeze(1)
    ent    = - (probs * (probs.clamp_min(1e-9)).log()).sum(dim=1, keepdim=True)
    state  = torch.cat([probs, max_p, ent, margin], dim=1)
    return state, probs, max_p, ent, margin


n_feats = len(train_cols_after_ratios)
n_classes = len(label_classes)

model = FeatureCNN_Attn(n_feats, n_classes, drop=0.35).to(DEVICE)
model.load_state_dict(torch.load(ROOT / "models/pytorch_tabular_cnn_best.pt", map_location=DEVICE))
model.eval()

temp = TemperatureScaler().to(DEVICE)
temp.load_state_dict(torch.load(ROOT / "models/temp_calibrator.pt", map_location=DEVICE))
temp.eval()

policy = RLDecisionLayer(in_dim=n_classes+3).to(DEVICE)
policy.load_state_dict(torch.load(ROOT / "RL/rl_policy_best.pt", map_location=DEVICE)["state_dict"])
policy.eval()


@torch.no_grad()
def rl_decide(model, temp, policy, xb):
    out = model(xb)
    logits = temp(out[0])
    state, probs, max_p, ent, margin = build_state_from_logits(logits)
    if USE_POLICY:
        logpi = policy(state)
        action = torch.argmax(logpi, dim=1)
    else:
        action = torch.ones((xb.size(0),), dtype=torch.long, device=xb.device)
    top2 = torch.topk(probs, k=2, dim=1).values
    m_p = top2[:, 0]
    m_g = (top2[:, 0] - top2[:, 1]).clamp_min(0)
    must_route = (m_p < ROUTE_TAU) | (m_g < ROUTE_MARGIN) | (ent.squeeze(1) > ROUTE_ENTROPY)
    action[must_route] = 1
    action[(m_p >= TAU) & (m_g >= MARGIN)] = 0
    action[m_p >= HARD_TAU] = 0
    pred = probs.argmax(dim=1)
    emb  = out[1]
    return action, pred, probs, emb


def predict_flow(row_like: Union[pd.Series, dict, pd.DataFrame]) -> dict:
    """Single-row prediction (returns structured dict)."""
    X_proc = preprocess_df(_to_1row_df(row_like))
    xb = torch.from_numpy(X_proc.values.astype(np.float32)).unsqueeze(1).to(DEVICE)
    action, pred, probs, emb = rl_decide(model, temp, policy, xb)
    pred_idx = int(pred.item())
    conf = float(probs[0, pred_idx])
    decision = "accepted" if action.item() == 0 else "routed"
    return {
        "class_label": str(label_classes[pred_idx]),
        "class_index": pred_idx,
        "confidence": conf,
        "decision": decision,
        "embedding": emb.squeeze(0).detach().cpu().numpy().tolist()
    }

def predict_batch(df: pd.DataFrame) -> pd.DataFrame:
    """Batch prediction for a DataFrame of flows."""
    X_proc = preprocess_df(df)
    xb = torch.from_numpy(X_proc.values.astype(np.float32)).unsqueeze(1).to(DEVICE)
    action, pred, probs, emb = rl_decide(model, temp, policy, xb)
    conf = probs.max(dim=1).values.detach().cpu().numpy()
    decisions = np.where(action.cpu().numpy() == 0, "accepted", "routed")
    preds = pred.cpu().numpy()
    labels = [label_classes[p] for p in preds]
    result_df = pd.DataFrame({
        "pred_class": labels,
        "pred_index": preds,
        "confidence": conf,
        "decision": decisions
    })
    result_df["embedding"] = [e.detach().cpu().numpy().tolist() for e in emb]
    return result_df


