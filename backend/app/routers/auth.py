from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.models import User
from app.schemas.schemas import LoginRequest, TokenResponse

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")  # rate-limit login attempts on the free public instance
async def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(subject=user.email, role=user.role)
    return TokenResponse(access_token=token)
