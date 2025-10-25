
import json, numpy as np, torch, joblib
from pathlib import Path

from app.pipeline.classifier import FeatureCNN_Attn, TemperatureScaler, RLDecisionLayer

ROOT = Path("app/pipeline/deepv14").resolve()
MANIFEST_PATH = ROOT/"logs"/"artifacts_manifest.json"

manifest = json.load(open(MANIFEST_PATH))
A = manifest["artifacts"]
RUNTIME = manifest.get("runtime", {})

MODEL_CFG = manifest.get("model_config", {})
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


shiftlog_params = joblib.load(ROOT / A["shiftlog_params"])
imp   = joblib.load(ROOT / A["imputer"])
vt    = joblib.load(ROOT / A["variance_threshold"])
robust= joblib.load(ROOT / A["robust_scaler"])
std   = joblib.load(ROOT / A["standard_scaler"])

kept_features      = json.load(open(ROOT / A["kept_features"]))
corr_dropped       = json.load(open(ROOT / A["corr_dropped"]))
train_feature_cols = json.load(open(ROOT / A["train_feature_cols"]))

classes            = np.load(ROOT / A["label_classes"], allow_pickle=True)

RATIO_NORM_PARAMS  = manifest.get("ratio_norm_params", None)

n_feats   = int(MODEL_CFG.get("n_feats", len(kept_features)))
n_classes = int(MODEL_CFG.get("n_classes", len(classes)))

model = FeatureCNN_Attn(n_feats=n_feats, n_classes=n_classes, drop=MODEL_CFG.get("dropout", 0.35)).to(DEVICE)
model.load_state_dict(torch.load(ROOT / A["cnn_state_dict"], map_location=DEVICE))
model.eval()

temp = TemperatureScaler().to(DEVICE)
temp.load_state_dict(torch.load(ROOT / A["temp_state_dict"], map_location=DEVICE))
temp.eval()

sd_policy = torch.load(ROOT / A["rl_policy"], map_location=DEVICE)
hidden_dim = int(sd_policy["net.0.weight"].shape[0])
in_dim_ckpt = int(sd_policy["net.0.weight"].shape[1])

policy = RLDecisionLayer(in_dim=n_classes + 3, hidden=hidden_dim).to(DEVICE)
policy.load_state_dict(sd_policy, strict=True)
policy.eval()


TAU       = float(RUNTIME.get("accept_thresholds", {}).get("TAU", 0.88))
HARD_TAU  = float(RUNTIME.get("accept_thresholds", {}).get("HARD_TAU", 0.95))
MARGIN    = float(RUNTIME.get("accept_thresholds", {}).get("MARGIN", 0.05))
USE_POLICY= bool(RUNTIME.get("use_policy", True))
HARD_GATE_AFTER_POLICY = bool(RUNTIME.get("hard_gate_after_policy", True))
ROUTE_TAU      = float(RUNTIME.get("route_thresholds", {}).get("ROUTE_TAU", 0.65))
ROUTE_MARGIN   = float(RUNTIME.get("route_thresholds", {}).get("ROUTE_MARGIN", 0.12))
ROUTE_ENTROPY  = float(RUNTIME.get("route_thresholds", {}).get("ROUTE_ENTROPY", 1.00))
ENTROPY_MAX    = float(RUNTIME.get("route_thresholds", {}).get("ENTROPY_MAX", 1.00))
