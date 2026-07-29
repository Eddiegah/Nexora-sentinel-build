"""
Loads the XGBoost model and SHAP explainer from ml/artifacts/ at startup.
The model_version is read from ml/artifacts/metrics.json so the API
can report which artifact is active without a code change.
"""
import json
import logging
import os
import pickle
from pathlib import Path
from typing import Optional

import xgboost as xgb

logger = logging.getLogger(__name__)

# Human-readable labels for each feature column.
# Update this mapping whenever the feature set changes in ml/train.py.
FEATURE_LABELS: dict[str, str] = {
    "rainfall_mm": "Rainfall (mm)",
    "avg_temp_c": "Average Temperature (°C)",
    "humidity_pct": "Relative Humidity (%)",
    "population_density": "Population Density (per km²)",
    "historical_cases": "Historical Malaria Cases",
}

# Feature columns in the exact order the model was trained on.
FEATURE_COLUMNS: list[str] = list(FEATURE_LABELS.keys())


class MLArtifacts:
    def __init__(self) -> None:
        self.model: Optional[xgb.XGBClassifier] = None
        self.explainer = None  # shap.TreeExplainer
        self.model_version: str = "unknown"
        self.loaded: bool = False

    def load(self, artifact_dir: str) -> None:
        path = Path(artifact_dir)
        model_path = path / "model.json"
        explainer_path = path / "explainer.pkl"
        metrics_path = path / "metrics.json"

        if not model_path.exists():
            logger.warning(
                "Model artifact not found at %s — predictions will be unavailable. "
                "Run ml/train.py to generate artifacts.",
                model_path,
            )
            return

        try:
            self.model = xgb.XGBClassifier()
            self.model.load_model(str(model_path))
            logger.info("XGBoost model loaded from %s", model_path)
        except Exception as exc:
            logger.error("Failed to load XGBoost model: %s", exc)
            return

        if explainer_path.exists():
            try:
                import shap
                with open(explainer_path, "rb") as f:
                    self.explainer = pickle.load(f)
                logger.info("SHAP explainer loaded from %s", explainer_path)
            except Exception as exc:
                logger.error("Failed to load SHAP explainer: %s", exc)
        else:
            logger.warning("SHAP explainer not found at %s", explainer_path)

        if metrics_path.exists():
            try:
                with open(metrics_path) as f:
                    metrics = json.load(f)
                self.model_version = metrics.get("model_version", "unknown")
            except Exception:
                pass

        self.loaded = self.model is not None and self.explainer is not None


# Singleton — imported and used across routers
artifacts = MLArtifacts()
