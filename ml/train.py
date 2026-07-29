"""
ml/train.py
───────────
Trains an XGBoost binary classifier on ingested region_indicators data,
then generates and saves a SHAP TreeExplainer.

Artifacts written to ml/artifacts/:
  model.json      — XGBoost model (JSON format, loadable without pickle)
  explainer.pkl   — SHAP TreeExplainer
  metrics.json    — evaluation metrics + model_version (from evaluate.py)

Usage:
    python ml/train.py
    python ml/train.py --data ml/artifacts/training_data.csv
"""
import argparse
import json
import logging
import os
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
FEATURE_COLUMNS = [
    "rainfall_mm",
    "avg_temp_c",
    "humidity_pct",
    "population_density",
    "historical_cases",
]


def load_data(data_path: Path) -> tuple[pd.DataFrame, pd.Series]:
    if not data_path.exists():
        logger.error(
            "Training data not found at %s. Run ml/fetch_training_data.py first.", data_path
        )
        sys.exit(1)
    df = pd.read_csv(data_path)
    X = df[FEATURE_COLUMNS]
    y = df["label"]
    logger.info("Loaded %d training examples (%d positive).", len(y), y.sum())
    return X, y


def train(X: pd.DataFrame, y: pd.Series) -> xgb.XGBClassifier:
    # Class imbalance — use scale_pos_weight to up-weight outbreak cases.
    neg, pos = (y == 0).sum(), (y == 1).sum()
    scale_pos_weight = neg / pos if pos > 0 else 1.0
    logger.info("scale_pos_weight=%.2f (neg=%d, pos=%d)", scale_pos_weight, neg, pos)

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        # Note: use_label_encoder was removed in XGBoost 2.0 — do not add it back
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X, y)
    logger.info("Model training complete.")
    return model


def build_explainer(model: xgb.XGBClassifier, X: pd.DataFrame):
    import shap
    logger.info("Building SHAP TreeExplainer…")
    explainer = shap.TreeExplainer(model)
    # Smoke-test: verify explainer runs on the training data.
    sample = X.iloc[:min(50, len(X))]
    _ = explainer.shap_values(sample)
    logger.info("SHAP explainer built successfully.")
    return explainer


def save_artifacts(model: xgb.XGBClassifier, explainer, version: str) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    model_path = ARTIFACTS_DIR / "model.json"
    model.save_model(str(model_path))
    logger.info("Model saved to %s", model_path)

    explainer_path = ARTIFACTS_DIR / "explainer.pkl"
    with open(explainer_path, "wb") as f:
        pickle.dump(explainer, f)
    logger.info("Explainer saved to %s", explainer_path)

    # Write / update model_version in metrics.json.
    metrics_path = ARTIFACTS_DIR / "metrics.json"
    metrics: dict = {}
    if metrics_path.exists():
        with open(metrics_path) as f:
            metrics = json.load(f)
    metrics["model_version"] = version
    metrics["trained_at"] = datetime.now(timezone.utc).isoformat()
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Metrics updated at %s  (version=%s)", metrics_path, version)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the Nexora Sentinel risk model.")
    parser.add_argument(
        "--data",
        default="ml/artifacts/training_data.csv",
        help="Path to training CSV produced by fetch_training_data.py",
    )
    parser.add_argument(
        "--version",
        default=datetime.now(timezone.utc).strftime("v%Y%m%d-%H%M"),
        help="Model version tag written to metrics.json (default: auto timestamp)",
    )
    args = parser.parse_args()

    X, y = load_data(Path(args.data))
    model = train(X, y)
    explainer = build_explainer(model, X)
    save_artifacts(model, explainer, args.version)

    logger.info("Training complete. Artifacts in %s", ARTIFACTS_DIR)


if __name__ == "__main__":
    main()
