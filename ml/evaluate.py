"""
ml/evaluate.py
──────────────
Evaluates the trained XGBoost model using a stratified train/test split.
Writes precision, recall, F1, AUC, and confusion matrix to
ml/artifacts/metrics.json alongside the existing model_version.

Usage:
    python ml/evaluate.py
    python ml/evaluate.py --data ml/artifacts/training_data.csv --test-size 0.2
"""
import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.model_selection import train_test_split

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the Nexora Sentinel risk model.")
    parser.add_argument("--data", default="ml/artifacts/training_data.csv")
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        logger.error("Training data not found at %s. Run fetch_training_data.py first.", data_path)
        sys.exit(1)

    model_path = ARTIFACTS_DIR / "model.json"
    if not model_path.exists():
        logger.error("Model not found at %s. Run train.py first.", model_path)
        sys.exit(1)

    df = pd.read_csv(data_path)
    X = df[FEATURE_COLUMNS]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, stratify=y, random_state=42
    )
    logger.info("Test set: %d examples (%d positive)", len(y_test), y_test.sum())

    model = xgb.XGBClassifier()
    model.load_model(str(model_path))

    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= 0.5).astype(int)

    auc = roc_auc_score(y_test, y_proba)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred).tolist()

    logger.info("AUC=%.4f  Precision=%.4f  Recall=%.4f  F1=%.4f", auc, precision, recall, f1)
    logger.info("Confusion matrix (TN FP / FN TP):\n%s", np.array(cm))

    # Merge into existing metrics.json (preserves model_version written by train.py).
    metrics_path = ARTIFACTS_DIR / "metrics.json"
    metrics: dict = {}
    if metrics_path.exists():
        with open(metrics_path) as f:
            metrics = json.load(f)

    metrics.update({
        "auc": round(auc, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "confusion_matrix": cm,
        "test_size_fraction": args.test_size,
        "test_n_samples": len(y_test),
        "test_n_positive": int(y_test.sum()),
    })

    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Metrics written to %s", metrics_path)


if __name__ == "__main__":
    main()
