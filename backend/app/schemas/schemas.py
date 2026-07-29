from datetime import datetime, date
from typing import Optional, Any
from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Regions ───────────────────────────────────────────────────────────────────

class RegionOut(BaseModel):
    id: int
    name: str
    country: str
    latitude: float
    longitude: float

    model_config = {"from_attributes": True}


# ── SHAP explanation ──────────────────────────────────────────────────────────

class ShapFeature(BaseModel):
    label: str          # human-readable label, e.g. "Rainfall (mm)"
    raw_name: str       # original column name, e.g. "rainfall_mm"
    shap_value: float   # signed SHAP contribution
    feature_value: Any  # actual value used for this prediction


class ShapExplanation(BaseModel):
    base_value: float
    features: list[ShapFeature]


# ── Predictions ───────────────────────────────────────────────────────────────

class PredictionOut(BaseModel):
    id: int
    region_id: int
    predicted_at: datetime
    risk_score: float
    risk_category: str
    model_version: str
    shap_explanation: ShapExplanation

    model_config = {"from_attributes": True}


class PredictionHistoryItem(BaseModel):
    predicted_at: datetime
    risk_score: float
    risk_category: str

    model_config = {"from_attributes": True}


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: Optional[str] = None
