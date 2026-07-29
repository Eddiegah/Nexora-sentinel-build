from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, Text, Double, Date, DateTime,
    ForeignKey, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    country = Column(Text, nullable=False)
    latitude = Column(Double, nullable=False)
    longitude = Column(Double, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    indicators = relationship("RegionIndicator", back_populates="region")
    predictions = relationship("Prediction", back_populates="region")


class RegionIndicator(Base):
    __tablename__ = "region_indicators"

    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    date = Column(Date, nullable=False)
    rainfall_mm = Column(Double)
    avg_temp_c = Column(Double)
    humidity_pct = Column(Double)
    population_density = Column(Double)
    historical_cases = Column(Integer)
    source = Column(Text, nullable=False)

    region = relationship("Region", back_populates="indicators")

    __table_args__ = (
        UniqueConstraint("region_id", "date", "source", name="uq_indicator_region_date_source"),
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    predicted_at = Column(DateTime(timezone=True), server_default=func.now())
    risk_score = Column(Double, nullable=False)
    risk_category = Column(Text, nullable=False)
    model_version = Column(Text, nullable=False)
    shap_explanation = Column(JSONB, nullable=False)

    region = relationship("Region", back_populates="predictions")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, nullable=False, default="health_worker")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
