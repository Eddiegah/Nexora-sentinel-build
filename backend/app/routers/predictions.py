import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.core.ml_loader import artifacts, FEATURE_COLUMNS, FEATURE_LABELS
from app.models.models import Region, RegionIndicator, Prediction
from app.schemas.schemas import (
    PredictionOut,
    PredictionHistoryItem,
    ShapExplanation,
    ShapFeature,
)

router = APIRouter(prefix="/regions", tags=["predictions"])

RISK_THRESHOLDS = {"low": 0.4, "medium": 0.7}


def _score_to_category(score: float) -> str:
    if score < RISK_THRESHOLDS["low"]:
        return "low"
    if score < RISK_THRESHOLDS["medium"]:
        return "medium"
    return "high"


def _build_shap_explanation(feature_row: dict, feature_values: np.ndarray) -> dict:
    """Run SHAP and build the structured explanation payload."""
    if artifacts.explainer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SHAP explainer not loaded. Run ml/train.py and restart the service.",
        )
    import shap

    shap_values = artifacts.explainer.shap_values(feature_values)

    # For binary classifiers shap_values may be shape (1, n_features) or (n_features,)
    if hasattr(shap_values, "__len__") and len(np.array(shap_values).shape) > 1:
        sv = np.array(shap_values)[0]  # take positive-class values
        if len(sv.shape) > 1:
            sv = sv[0]
    else:
        sv = np.array(shap_values)[0]

    base_value = float(
        artifacts.explainer.expected_value[1]
        if hasattr(artifacts.explainer.expected_value, "__len__")
        else artifacts.explainer.expected_value
    )

    features = [
        ShapFeature(
            label=FEATURE_LABELS.get(col, col),
            raw_name=col,
            shap_value=float(sv[i]),
            feature_value=feature_row.get(col),
        )
        for i, col in enumerate(FEATURE_COLUMNS)
    ]
    # Sort by absolute SHAP value descending so most influential features come first.
    features.sort(key=lambda f: abs(f.shap_value), reverse=True)

    return ShapExplanation(base_value=base_value, features=features)


@router.get("/{region_id}/predictions/latest", response_model=PredictionOut)
def get_latest_prediction(
    region_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> PredictionOut:
    """Return the most recent prediction + SHAP explanation for a region."""
    pred = (
        db.query(Prediction)
        .filter(Prediction.region_id == region_id)
        .order_by(Prediction.predicted_at.desc())
        .first()
    )
    if not pred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No predictions found for this region.",
        )
    return pred


@router.get("/{region_id}/predictions/history", response_model=list[PredictionHistoryItem])
def get_prediction_history(
    region_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[PredictionHistoryItem]:
    """Return the time-series of past predictions for a region (for trend charts)."""
    preds = (
        db.query(Prediction)
        .filter(Prediction.region_id == region_id)
        .order_by(Prediction.predicted_at.asc())
        .all()
    )
    return preds


@router.post("/{region_id}/predict", response_model=PredictionOut)
def trigger_prediction(
    region_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> PredictionOut:
    """
    Trigger a fresh prediction using the latest stored indicators for this region.
    Requires admin role. The result (including SHAP explanation) is stored in Postgres.
    """
    if not artifacts.loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML model not loaded. Run ml/train.py and restart the service.",
        )

    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Region not found.")

    # Fetch the latest indicator row for this region.
    indicator = (
        db.query(RegionIndicator)
        .filter(RegionIndicator.region_id == region_id)
        .order_by(RegionIndicator.date.desc())
        .first()
    )
    if not indicator:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No indicator data available for this region. Run the ingestion job first.",
        )

    feature_row = {
        "rainfall_mm": indicator.rainfall_mm or 0.0,
        "avg_temp_c": indicator.avg_temp_c or 0.0,
        "humidity_pct": indicator.humidity_pct or 0.0,
        "population_density": indicator.population_density or 0.0,
        "historical_cases": float(indicator.historical_cases or 0),
    }
    feature_values = np.array([[feature_row[col] for col in FEATURE_COLUMNS]])

    # Predict probability of outbreak (positive class).
    proba = artifacts.model.predict_proba(feature_values)[0][1]
    risk_score = float(proba)
    risk_category = _score_to_category(risk_score)

    shap_explanation = _build_shap_explanation(feature_row, feature_values)

    prediction = Prediction(
        region_id=region_id,
        risk_score=risk_score,
        risk_category=risk_category,
        model_version=artifacts.model_version,
        shap_explanation=shap_explanation.model_dump(),
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction
