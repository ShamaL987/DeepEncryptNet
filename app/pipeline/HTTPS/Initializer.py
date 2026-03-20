from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import joblib

import torch

from app.pipeline.HTTPS.helpers import _read_json, _ensure_df, _coerce_numeric, _softmax_np, _probs_to_state
from app.pipeline.HTTPS.models import FeatureCNN_Attn, RLDecisionLayer


class HTTPSInference:
    """Inference that requires ONLY kept_features.json columns in the incoming DataFrame."""

    def __init__(self, bundle_dir, device: Optional[torch.device] = None):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.bundle_dir = bundle_dir

        self.logs_dir = self.bundle_dir / "logs"
        self.preprocess_dir = self.bundle_dir / "preprocess"
        self.models_dir = self.bundle_dir / "models"

        self.bundle_meta = _read_json(self.bundle_dir / "inference_bundle.json")
        self.config = _read_json(self.logs_dir / "config.json")

        # Classes
        classes_obj = _read_json(self.logs_dir / "classes.json")
        self.classes: List[str] = [str(x) for x in classes_obj["classes"]]
        self.n_classes = int(len(self.classes))

        # Final model input features
        kept_obj = _read_json(self.logs_dir / "kept_features.json")
        self.kept_features: List[str] = [str(x) for x in kept_obj["kept_features"]]

        # Load preprocess artifacts
        self.shiftlog_params = joblib.load(self.preprocess_dir / "shiftlog_params.joblib")
        self.imputer = joblib.load(self.preprocess_dir / "imputer_median.joblib")
        self.robust = joblib.load(self.preprocess_dir / "robust_scaler.joblib")
        self.standard = joblib.load(self.preprocess_dir / "standard_scaler.joblib")

        # Build per-kept-feature shift/log/median vectors
        shift_all = np.asarray(self.shiftlog_params["shift"], dtype=float)
        log_mask_all = np.asarray(self.shiftlog_params["log_mask"], dtype=bool)

        # imputer.statistics_ is aligned to the columns used at fit time (train_feature_cols order)
        stats_all = np.asarray(self.imputer.statistics_, dtype=float)
        idxs = np.arange(len(self.kept_features), dtype=int)


        self.shift_vec = shift_all[idxs]
        self.log_mask_vec = log_mask_all[idxs]
        self.median_vec = stats_all[idxs]

        # CNN
        model_drop = float(self.config.get("MODEL_DROP", 0.35))
        self.cnn = FeatureCNN_Attn(n_classes=self.n_classes, drop=model_drop)

        cnn_fp = self.models_dir / self.bundle_meta.get("model_file", "cnn_best.pt")
        cnn_ckpt = torch.load(cnn_fp, map_location="cpu")
        state_dict = cnn_ckpt["state_dict"] if isinstance(cnn_ckpt, dict) and "state_dict" in cnn_ckpt else cnn_ckpt
        self.cnn.load_state_dict(state_dict)
        self.cnn.to(self.device)
        self.cnn.eval()

        # Temperature usage decision
        self.use_temperature_for_routing = bool(self.bundle_meta.get("use_temperature_for_routing", False))
        self.selected_probs_variant = str(self.bundle_meta.get("selected_probs_variant", "raw"))
        self.temperature_T: Optional[float] = None

        if self.use_temperature_for_routing:
            temp_fp = self.models_dir / self.bundle_meta.get("temperature_scaler_file", "temperature_scaler.pt")

            if temp_fp.exists():
                t_ckpt = torch.load(temp_fp, map_location="cpu")
                T = t_ckpt.get("T", None)

                if T is None and isinstance(t_ckpt, dict) and "state_dict" in t_ckpt and "log_t" in t_ckpt[
                    "state_dict"]:
                    self.temperature_T = float(torch.exp(t_ckpt["state_dict"]["log_t"]).item())
                else:
                    self.temperature_T = float(T) if T is not None else None

            if self.temperature_T is None:
                self.use_temperature_for_routing = False
                self.selected_probs_variant = "raw"

        # RL policy (optional)
        self.rl_policy: Optional[RLDecisionLayer] = None
        rl_fp = self.models_dir / self.bundle_meta.get("rl_policy_file", "rl_policy.pt")
        if rl_fp.exists():
            rl_ckpt = torch.load(rl_fp, map_location="cpu")
            state_dim = int(rl_ckpt["state_dim"])
            hidden = int(rl_ckpt.get("hidden", 64))
            self.rl_policy = RLDecisionLayer(state_dim, hidden=hidden)
            self.rl_policy.load_state_dict(rl_ckpt["state_dict"])
            self.rl_policy.to(self.device)
            self.rl_policy.eval()

        # tau (optional)
        self.tau: Optional[float] = None
        tau_fp = self.logs_dir / "routing_tau.json"
        if tau_fp.exists():
            self.tau = float(_read_json(tau_fp).get("tau"))

    def validate_input(self, df: pd.DataFrame) -> None:
        got = set(df.columns.astype(str).tolist())
        required = set(self.kept_features)
        missing = sorted(list(required - got))
        if missing:
            raise ValueError(
                f"Input DataFrame must contain ALL kept_features ({len(required)}).\n"
                f"Missing ({len(missing)}): {missing[:50]}{' ...' if len(missing) > 50 else ''}"
            )

    def preprocess(self, df: pd.DataFrame) -> np.ndarray:
        self.validate_input(df)

        # Only take kept_features (ignore extras)
        X = df.reindex(columns=self.kept_features)
        X = _coerce_numeric(X, self.kept_features)

        arr = X.values.astype(float)

        # Apply shift
        arr = arr + self.shift_vec

        # Apply log1p only where training said it's needed
        if self.log_mask_vec.any():
            mask = self.log_mask_vec
            arr[:, mask] = np.maximum(arr[:, mask], -0.999999)
            arr[:, mask] = np.log1p(arr[:, mask])

        # Replace inf -> nan
        arr = np.where(np.isfinite(arr), arr, np.nan)

        # Median impute using training medians
        # (same values SimpleImputer learned, but applied columnwise for this subset)
        arr = np.where(np.isnan(arr), self.median_vec, arr)

        # Scale (scalers were fit on kept_features order)
        X_r = self.robust.transform(arr)
        X_n = self.standard.transform(X_r)
        return np.asarray(X_n, dtype=np.float32)

    @torch.no_grad()
    def _cnn_forward(self, Xn: np.ndarray, batch_size: int = 512) -> Tuple[np.ndarray, np.ndarray]:
        logits_all, emb_all = [], []
        for i in range(0, len(Xn), batch_size):
            xb = torch.tensor(Xn[i:i + batch_size], dtype=torch.float32, device=self.device).unsqueeze(1)
            logits, emb = self.cnn(xb)
            logits_all.append(logits.detach().cpu().numpy())
            emb_all.append(emb.detach().cpu().numpy())
        return np.concatenate(logits_all, axis=0), np.concatenate(emb_all, axis=0)

    def logits_to_probs_selected(self, logits: np.ndarray) -> np.ndarray:
        if self.use_temperature_for_routing and self.temperature_T:
            return _softmax_np(logits / float(self.temperature_T))
        return _softmax_np(logits)

    @torch.no_grad()
    def rl_actions(self, probs: np.ndarray, batch: int = 4096) -> Optional[np.ndarray]:
        if self.rl_policy is None:
            return None
        state = _probs_to_state(probs)
        acts = []
        for i in range(0, len(state), batch):
            sb = torch.tensor(state[i:i + batch], dtype=torch.float32, device=self.device)
            q = self.rl_policy(sb)
            acts.append(q.argmax(dim=1).detach().cpu().numpy())
        return np.concatenate(acts, axis=0)

    def threshold_actions(self, probs: np.ndarray) -> Optional[np.ndarray]:
        if self.tau is None:
            return None
        conf = probs.max(axis=1)
        return np.where(conf >= float(self.tau), 0, 1).astype(int)

    def predict(
            self,
            features_df: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]],
            batch_size: int = 512,
            return_probs: bool = False,
            return_embeddings: bool = False,
    ) -> pd.DataFrame:
        df = _ensure_df(features_df)
        Xn = self.preprocess(df)

        logits, emb = self._cnn_forward(Xn, batch_size=batch_size)
        probs = self.logits_to_probs_selected(logits)

        pred_id = probs.argmax(axis=1).astype(int)
        conf = probs.max(axis=1).astype(float)

        state = _probs_to_state(probs)
        entropy = state[:, -2].astype(float)
        margin = state[:, -1].astype(float)

        pred_label = [self.classes[i] for i in pred_id]

        out = pd.DataFrame(
            {
                "pred_class": pred_label,
                "pred_class_id": pred_id,
                "confidence": conf,
                "entropy": entropy,
                "top2_margin": margin,
                "use_temperature_for_routing": bool(self.use_temperature_for_routing),
                "selected_probs_variant": str(self.selected_probs_variant),
                "temperature_T": float(self.temperature_T) if self.temperature_T is not None else np.nan,
                "tau": float(self.tau) if self.tau is not None else np.nan,
            },
            index=df.index,
        )

        a_thr = self.threshold_actions(probs)
        if a_thr is not None:
            out["action_threshold"] = a_thr.astype(int)
            out["decision_threshold"] = np.where(a_thr == 0, "accept", "route")
        else:
            out["action_threshold"] = np.nan
            out["decision_threshold"] = None

        a_rl = self.rl_actions(probs)
        if a_rl is not None:
            out["action_rl"] = a_rl.astype(int)
            out["decision_rl"] = np.where(a_rl == 0, "accept", "route")
        else:
            out["action_rl"] = np.nan
            out["decision_rl"] = None

        if return_probs:
            prob_cols = [f"p_{c}" for c in self.classes]
            out = pd.concat([out, pd.DataFrame(probs, columns=prob_cols, index=df.index)], axis=1)

        if return_embeddings:
            emb_cols = [f"emb_{i}" for i in range(emb.shape[1])]
            out = pd.concat([out, pd.DataFrame(emb, columns=emb_cols, index=df.index)], axis=1)

        return out