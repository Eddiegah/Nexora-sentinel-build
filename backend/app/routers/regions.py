from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Region
from app.schemas.schemas import RegionOut

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("", response_model=list[RegionOut])
def list_regions(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[RegionOut]:
    """Return all supported regions."""
    return db.query(Region).order_by(Region.country, Region.name).all()


@router.get("/{region_id}", response_model=RegionOut)
def get_region(
    region_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> RegionOut:
    """Return a single region by ID."""
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Region not found.")
    return region
