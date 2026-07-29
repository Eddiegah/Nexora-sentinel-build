import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.ml_loader import artifacts
from app.routers import auth, regions, predictions
from app.schemas.schemas import HealthResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load ML artifacts once at startup so predictions are fast.
    logger.info("Loading ML artifacts from '%s'...", settings.model_artifact_path)
    artifacts.load(settings.model_artifact_path)
    if artifacts.loaded:
        logger.info("ML artifacts loaded. Model version: %s", artifacts.model_version)
    else:
        logger.warning(
            "ML artifacts NOT loaded — /predict endpoints will return 503 until "
            "ml/train.py is run and the service is restarted."
        )
    yield
    # Shutdown: nothing to clean up for XGBoost.


app = FastAPI(
    title="Nexora Sentinel API",
    description="AI-powered malaria outbreak risk prediction for Africa.",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiter (used by auth router)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — allow the Vercel frontend and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers — predictions must be registered before regions so that
# /regions/{id}/predictions/... routes take precedence over /regions/{id}
app.include_router(auth.router)
app.include_router(predictions.router)
app.include_router(regions.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """
    Liveness endpoint used by the frontend to detect cold-start wake-up.
    Returns 200 as soon as the service is running; the frontend polls this
    and hides the 'waking up' banner once it responds.
    """
    return HealthResponse(
        status="ok",
        model_loaded=artifacts.loaded,
        model_version=artifacts.model_version if artifacts.loaded else None,
    )
