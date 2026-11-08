"""
Нормальное обучение модели development_score.

Данные ближе к реальности:
- плотность: логнормаль от сельской до урбан-кора
- target согласован с индикаторами (нелинейно, с взаимодействиями)
- больше примеров, проверка на hold-out + CV
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

N_SAMPLES = 12000
ROOT = Path(__file__).parent.parent
MODELS_DIR = ROOT / "models"
DATA_DIR = ROOT / "data"
MODELS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


def make_dataset(n: int) -> pd.DataFrame:
    """Синтетика, похожая на реальные распределения."""
    rng = np.random.RandomState(RANDOM_STATE)

    # Смесь: 40% низкая плотность, 35% средняя, 25% высокая
    mix = rng.choice([0, 1, 2], size=n, p=[0.40, 0.35, 0.25])
    population_density = np.empty(n)
    for i, m in enumerate(mix):
        if m == 0:
            population_density[i] = np.exp(rng.uniform(np.log(10), np.log(800)))
        elif m == 1:
            population_density[i] = np.exp(rng.uniform(np.log(600), np.log(4500)))
        else:
            population_density[i] = np.exp(rng.uniform(np.log(3500), np.log(18000)))

    # Зелень обратно связана с плотностью + шум
    dens_norm = np.clip(np.log1p(population_density) / np.log1p(18000), 0, 1)
    green_space_ratio = np.clip(
        0.45 - 0.32 * dens_norm + rng.normal(0, 0.06, n),
        0.02,
        0.55,
    )

    # Инфра / транспорт / экономика — растут с «городскостью», но не линейно
    infrastructure_index = np.clip(
        0.12 + 0.70 * dens_norm**0.85 + rng.normal(0, 0.07, n),
        0.05,
        0.98,
    )
    transport_access = np.clip(
        0.08 + 0.65 * dens_norm**0.9 + 0.15 * infrastructure_index + rng.normal(0, 0.06, n),
        0.04,
        0.98,
    )
    economic_activity = np.clip(
        0.10
        + 0.45 * dens_norm
        + 0.30 * infrastructure_index
        + 0.10 * transport_access
        + rng.normal(0, 0.06, n),
        0.05,
        0.98,
    )

    # Target: осмысленная комбинация (не «всё = плотность»)
    # Высокая плотность без инфра/экономики ≠ высокий development
    score = (
        18 * dens_norm
        + 22 * infrastructure_index
        + 18 * transport_access
        + 20 * economic_activity
        + 12 * green_space_ratio
        + 10 * (infrastructure_index * economic_activity)
        + 8 * (transport_access * dens_norm)
        - 6 * (dens_norm * (1 - infrastructure_index))  # перенаселённость без инфра
        + rng.normal(0, 2.5, n)
    )
    # Масштаб 0–100
    score = (score - score.min()) / (score.max() - score.min() + 1e-9) * 100
    score = np.clip(score + rng.normal(0, 1.5, n), 0, 100)

    df = pd.DataFrame(
        {
            "population_density": population_density,
            "green_space_ratio": green_space_ratio,
            "infrastructure_index": infrastructure_index,
            "transport_access": transport_access,
            "economic_activity": economic_activity,
            "development_score": score,
        }
    )
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["log_density"] = np.log1p(out["population_density"])
    out["density_x_infra"] = (out["population_density"] / 20000.0) * out["infrastructure_index"]
    out["green_x_transport"] = out["green_space_ratio"] * out["transport_access"]
    out["infra_x_econ"] = out["infrastructure_index"] * out["economic_activity"]
    out["urban_balance"] = out["infrastructure_index"] * out["economic_activity"] * (
        1.0 - np.abs(out["green_space_ratio"] - 0.2)
    )
    out["congestion_proxy"] = out["log_density"] * (1.0 - out["transport_access"])
    return out


FEATURE_COLS = [
    "population_density",
    "green_space_ratio",
    "infrastructure_index",
    "transport_access",
    "economic_activity",
    "log_density",
    "density_x_infra",
    "green_x_transport",
    "infra_x_econ",
    "urban_balance",
    "congestion_proxy",
]


def main():
    print("=" * 56)
    print("Обучение модели development_score (нормальный прогон)")
    print("=" * 56)

    df = make_dataset(N_SAMPLES)
    df = add_features(df)
    df.to_csv(DATA_DIR / "training_samples.csv", index=False)
    print(f"Датасет: {len(df)} строк → data/training_samples.csv")
    print(df[["population_density", "development_score"]].describe().round(2))

    X = df[FEATURE_COLS]
    y = df["development_score"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )

    candidates = {
        "HistGradientBoosting": HistGradientBoostingRegressor(
            max_iter=400,
            learning_rate=0.05,
            max_depth=8,
            min_samples_leaf=20,
            l2_regularization=0.1,
            random_state=RANDOM_STATE,
        ),
        "GradientBoosting": GradientBoostingRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=5,
            min_samples_leaf=8,
            subsample=0.85,
            random_state=RANDOM_STATE,
        ),
        "RandomForest": RandomForestRegressor(
            n_estimators=250,
            max_depth=16,
            min_samples_leaf=4,
            max_features="sqrt",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }

    results = {}
    best_name, best_score, best_model = None, -np.inf, None

    for name, model in candidates.items():
        print(f"\n→ {name} ...")
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, pred)
        rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
        r2 = r2_score(y_test, pred)
        cv = cross_val_score(model, X_train, y_train, cv=5, scoring="r2", n_jobs=-1)
        results[name] = {
            "mae": round(float(mae), 3),
            "rmse": round(rmse, 3),
            "r2": round(float(r2), 4),
            "cv_r2_mean": round(float(cv.mean()), 4),
            "cv_r2_std": round(float(cv.std()), 4),
        }
        print(
            f"   MAE={mae:.3f}  RMSE={rmse:.3f}  R²={r2:.4f}  "
            f"CV-R²={cv.mean():.4f}±{cv.std():.4f}"
        )
        if r2 > best_score:
            best_score, best_name, best_model = r2, name, model

    print(f"\n★ Лучшая: {best_name} (R²={best_score:.4f})")

    # Sanity: низкая плотность / слабая инфра → низкий score
    probe = pd.DataFrame(
        [
            {
                "population_density": 80,
                "green_space_ratio": 0.4,
                "infrastructure_index": 0.15,
                "transport_access": 0.12,
                "economic_activity": 0.12,
            },
            {
                "population_density": 9000,
                "green_space_ratio": 0.12,
                "infrastructure_index": 0.85,
                "transport_access": 0.88,
                "economic_activity": 0.9,
            },
            {
                "population_density": 12000,
                "green_space_ratio": 0.05,
                "infrastructure_index": 0.25,
                "transport_access": 0.2,
                "economic_activity": 0.2,
            },
        ]
    )
    probe = add_features(probe)
    probe_pred = best_model.predict(probe[FEATURE_COLS])
    print("\nПроверка здравого смысла:")
    print(f"  село/слабая инфра     → {probe_pred[0]:.1f}")
    print(f"  сильный урбан-центр   → {probe_pred[1]:.1f}")
    print(f"  плотно, но без инфра  → {probe_pred[2]:.1f}")

    joblib.dump(best_model, MODELS_DIR / "development_model.joblib")
    joblib.dump(FEATURE_COLS, MODELS_DIR / "feature_names.joblib")

    meta = {
        "version": "3.0",
        "best_model": best_name,
        "n_samples": N_SAMPLES,
        "features": FEATURE_COLS,
        "metrics": results,
        "selected_metrics": results[best_name],
        "sanity_check": {
            "low_development": round(float(probe_pred[0]), 2),
            "high_urban": round(float(probe_pred[1]), 2),
            "dense_weak_infra": round(float(probe_pred[2]), 2),
        },
        "dataset": "data/training_samples.csv",
    }
    with open(MODELS_DIR / "model_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\nСохранено → {MODELS_DIR / 'development_model.joblib'}")
    print(f"Мета       → {MODELS_DIR / 'model_meta.json'}")


if __name__ == "__main__":
    main()
