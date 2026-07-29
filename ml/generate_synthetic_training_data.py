"""
ml/generate_synthetic_training_data.py
───────────────────────────────────────
Generates realistic synthetic training data for the 10 seeded African regions
and writes it directly to Postgres AND to ml/artifacts/training_data.csv.

This is used ONCE to bootstrap the model before real ingestion data accumulates.
The data is based on published climate norms and WHO malaria burden statistics.

After the GitHub Actions ingest cron has run for a few weeks, retrain with
ml/train.py using the real data from ml/fetch_training_data.py instead.
"""
import os
import random
import logging
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Regional climate + disease profiles ──────────────────────────────────────
# Based on: WorldClim normals, WHO World Malaria Report 2023, WorldPop 2020
REGIONS = [
    # (id, name, country, lat, lon, rain_mu, rain_sd, temp_mu, temp_sd, hum_mu, hum_sd, pop_density, annual_cases_base)
    (1,  "Kampala",       "Uganda",     0.3476,  32.5825, 4.2, 3.8, 22.1, 1.5, 78, 8,  3800,  492000),
    (2,  "Nairobi",       "Kenya",     -1.2921,  36.8219, 3.1, 3.2, 17.8, 2.1, 65, 9,  4700,   79500),
    (3,  "Dar es Salaam", "Tanzania",  -6.7924,  39.2083, 3.8, 3.5, 26.4, 1.2, 80, 7,  3200,  297500),
    (4,  "Accra",         "Ghana",      5.6037,  -0.1870, 3.5, 3.1, 27.9, 1.3, 74, 8,  2900,  558000),
    (5,  "Lagos",         "Nigeria",    6.5244,   3.3792, 5.1, 4.2, 27.5, 1.1, 82, 7,  6500, 3360000),
    (6,  "Kinshasa",      "DRC",       -4.4419,  15.2663, 5.8, 4.5, 25.2, 1.4, 85, 6,  2200, 1520000),
    (7,  "Lusaka",        "Zambia",   -15.4167,  28.2833, 3.9, 4.1, 22.5, 2.3, 62, 10, 1800,  396000),
    (8,  "Lilongwe",      "Malawi",   -13.9626,  33.7741, 3.6, 3.9, 21.8, 2.1, 67, 9,  1500,  261000),
    (9,  "Maputo",        "Mozambique",-25.9692, 32.5732, 2.9, 3.4, 23.1, 2.8, 71, 9,  1200,  350000),
    (10, "Antananarivo",  "Madagascar",-18.9137, 47.5361, 3.2, 3.6, 18.9, 2.5, 73, 8,   900,  126000),
]

FEATURE_COLUMNS = ["rainfall_mm", "avg_temp_c", "humidity_pct", "population_density", "historical_cases"]


def generate_region_data(region: tuple, n_days: int = 730, seed: int = 42) -> pd.DataFrame:
    (rid, name, country, lat, lon,
     rain_mu, rain_sd, temp_mu, temp_sd,
     hum_mu, hum_sd, pop_density, annual_cases) = region

    rng = np.random.default_rng(seed + rid)

    # Daily climate with seasonal variation
    days = [date(2024, 1, 1) + timedelta(days=i) for i in range(n_days)]
    day_of_year = np.array([d.timetuple().tm_yday for d in days])

    # Rainfall peaks mid-year for East Africa, opposite for Southern Africa
    season_phase = -1.0 if lat < -10 else 1.0
    rain_season = rain_mu + 2.0 * np.sin(2 * np.pi * day_of_year / 365 * season_phase)
    rainfall = np.clip(rng.normal(rain_season, rain_sd, n_days), 0, None)

    temp_season = temp_mu + 2.0 * np.cos(2 * np.pi * day_of_year / 365 * season_phase)
    temperature = rng.normal(temp_season, temp_sd, n_days)

    humidity = np.clip(rng.normal(hum_mu, hum_sd, n_days), 20, 100)

    # Daily case estimate (annual / 365 with seasonal spike during rainy season)
    daily_base = annual_cases / 365.0
    case_season = daily_base * (1 + 0.8 * np.sin(2 * np.pi * day_of_year / 365 * season_phase + 1.5))
    cases = np.clip(rng.normal(case_season, case_season * 0.3, n_days), 0, None).astype(int)

    df = pd.DataFrame({
        "region_id": rid,
        "date": [d.isoformat() for d in days],
        "rainfall_mm": rainfall.round(1),
        "avg_temp_c": temperature.round(1),
        "humidity_pct": humidity.round(1),
        "population_density": float(pop_density),
        "historical_cases": cases,
    })
    return df


def generate_all(n_days: int = 730) -> pd.DataFrame:
    frames = [generate_region_data(r, n_days) for r in REGIONS]
    df = pd.concat(frames, ignore_index=True)

    # Label: 1 if cases exceed 75th percentile across ALL records
    threshold = df["historical_cases"].quantile(0.75)
    df["label"] = (df["historical_cases"] > threshold).astype(int)

    logger.info(
        "Generated %d rows, %d positive labels (threshold=%.0f daily cases)",
        len(df), df["label"].sum(), threshold,
    )
    return df


def write_to_csv(df: pd.DataFrame, path: str = "ml/artifacts/training_data.csv") -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    logger.info("Training data written to %s", out)


def write_to_postgres(df: pd.DataFrame, database_url: str) -> None:
    """Bulk upsert synthetic rows into region_indicators."""
    import re
    from sqlalchemy import create_engine, text

    url = database_url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    url = re.sub(r"[?&](sslmode|channel_binding)=[^&]*", "", url).rstrip("?")
    is_neon = "neon" in database_url
    connect_args = {"sslmode": "require"} if is_neon else {}

    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)

    # Build bulk insert in chunks of 500 rows
    df_insert = df[["region_id", "date", "rainfall_mm", "avg_temp_c",
                    "humidity_pct", "population_density", "historical_cases"]].copy()
    df_insert["source"] = "synthetic-bootstrap"

    records = df_insert.to_dict("records")
    chunk_size = 500
    total = 0

    with engine.begin() as conn:
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            conn.execute(text("""
                INSERT INTO region_indicators
                    (region_id, date, rainfall_mm, avg_temp_c, humidity_pct,
                     population_density, historical_cases, source)
                VALUES
                    (:region_id, :date, :rainfall_mm, :avg_temp_c, :humidity_pct,
                     :population_density, :historical_cases, :source)
                ON CONFLICT (region_id, date, source) DO NOTHING
            """), chunk)
            total += len(chunk)
            logger.info("  Inserted chunk %d/%d (%d rows)", i // chunk_size + 1,
                       (len(records) + chunk_size - 1) // chunk_size, len(chunk))

    logger.info("Upserted %d rows into region_indicators (source=synthetic-bootstrap)", total)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=730, help="Days of synthetic data (default: 730 = 2 years)")
    parser.add_argument("--csv-only", action="store_true", help="Write CSV only, skip Postgres")
    args = parser.parse_args()

    df = generate_all(n_days=args.days)
    write_to_csv(df)

    if not args.csv_only:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            logger.warning("DATABASE_URL not set — skipping Postgres write. CSV is available.")
        else:
            write_to_postgres(df, db_url)
            logger.info("Done — Postgres populated with bootstrap data.")
    else:
        logger.info("Done — CSV only mode.")
