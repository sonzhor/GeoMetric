"""Load the trained model and make predictions."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import joblib
import numpy as np
import pandas as pd

MODELS_DIR = Path(__file__).parent.parent / "models"
MODEL_PATH = MODELS_DIR / "development_model.joblib"
FEATURES_PATH = MODELS_DIR / "feature_names.joblib"

_model = None
_feature_names: List[str] | None = None


def _load():
    global _model, _feature_names
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. Run ml/train_model.py first."
            )
        _model = joblib.load(MODEL_PATH)
        _feature_names = joblib.load(FEATURES_PATH)
    return _model, _feature_names


def _enrich_features(indicators: Dict[str, float]) -> Dict[str, float]:
    dens = float(indicators["population_density"])
    green = float(indicators["green_space_ratio"])
    infra = float(indicators["infrastructure_index"])
    transport = float(indicators["transport_access"])
    econ = float(indicators["economic_activity"])

    log_density = float(np.log1p(dens))
    enriched = dict(indicators)
    enriched["log_density"] = log_density
    enriched["density_x_infra"] = (dens / 20000.0) * infra
    enriched["green_x_transport"] = green * transport
    enriched["infra_x_econ"] = infra * econ
    enriched["urban_balance"] = infra * econ * (1.0 - abs(green - 0.2))
    enriched["congestion_proxy"] = log_density * (1.0 - transport)
    return enriched


def predict_development(indicators: Dict[str, float]) -> Dict[str, Any]:
    model, feature_names = _load()
    full = _enrich_features(indicators)

    row = {f: full.get(f, 0.0) for f in feature_names}
    X = pd.DataFrame([row], columns=feature_names)

    score = float(model.predict(X)[0])
    score = max(0.0, min(100.0, score))

    top_factors = []
    importances = getattr(model, "feature_importances_", None)
    if importances is None and hasattr(model, "feature_importances_"):
        importances = model.feature_importances_

    # HistGradientBoosting has no feature_importances_ in older sklearn — skip gracefully
    if importances is not None:
        sorted_idx = np.argsort(importances)[::-1]
        base = {
            "population_density",
            "green_space_ratio",
            "infrastructure_index",
            "transport_access",
            "economic_activity",
        }
        for i in sorted_idx:
            name = feature_names[i]
            if name in base or len(top_factors) < 3:
                top_factors.append(
                    {
                        "feature": name,
                        "importance": round(float(importances[i]), 3),
                        "value": round(float(full.get(name, 0)), 4),
                    }
                )
            if len(top_factors) >= 4:
                break
    else:
        # fallback: show base indicators by absolute contribution heuristic
        for name in [
            "infrastructure_index",
            "economic_activity",
            "transport_access",
            "population_density",
        ]:
            if name in full:
                top_factors.append(
                    {
                        "feature": name,
                        "importance": None,
                        "value": round(float(full[name]), 4),
                    }
                )

    return {
        "development_score": round(score, 2),
        "top_contributing_factors": top_factors,
    }
