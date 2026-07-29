"""
ml/fetch_training_data.py
─────────────────────────
Pulls historical region_indicators + matching prediction labels from Postgres
and returns a clean Pandas DataFrame ready for ml/train.py.

Usage (standalone):
    python ml/fetch_training_data.py --output ml/artifacts/training_data.csv

The "label" column is 1 (outbreak) if historical_cases exceeds the 75th
percentile across all records, else 0.  This threshold can be overridden
with --outbreak-percentile.
"""
import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "rainfall_mm",
    "avg_temp_c",
    "humidity_pct",
    "population_density",
    "historical_cases",
]


def fetch(database_url: str, outbreak_percentile: float = 75.0) -> pd.DataFrame:
    url = database_url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    import re
    url = re.sub(r"[?&](sslmode|channel_binding)=[^&]*", "", url).rstrip("?")
    is_neon = "neon" in database_url
    connect_args = {"sslmode": "require"} if is_neon else {}
    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    query = text("""
        SELECT
            ri.region_id,
            ri.date,
            ri.rainfall_mm,
            ri.avg_temp_c,
            ri.humidity_pct,
            ri.population_density,
            ri.historical_cases
        FROM region_indicators ri
        ORDER BY ri.region_id, ri.date
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    logger.info("Fetched %d rows from region_indicators.", len(df))

    # Drop rows where any feature is entirely null.
    df = df.dropna(subset=FEATURE_COLUMNS, how="all")

    # Fill remaining NaNs with column medians.
    for col in FEATURE_COLUMNS:
        if df[col].isna().any():
            median = df[col].median()
            df[col] = df[col].fillna(median)
            logger.info("Filled %s NaNs with median %.2f", col, median)

    # Create binary outbreak label based on historical_cases percentile.
    threshold = df["historical_cases"].quantile(outbreak_percentile / 100)
    df["label"] = (df["historical_cases"] > threshold).astype(int)
    logger.info(
        "Outbreak threshold (%.0fth percentile): %.1f cases  →  %d positive labels / %d total",
        outbreak_percentile,
        threshold,
        df["label"].sum(),
        len(df),
    )

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch training data from Postgres.")
    parser.add_argument(
        "--output",
        default="ml/artifacts/training_data.csv",
        help="Path to write the CSV (default: ml/artifacts/training_data.csv)",
    )
    parser.add_argument(
        "--outbreak-percentile",
        type=float,
        default=75.0,
        help="historical_cases percentile threshold for positive label (default: 75)",
    )
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL environment variable is not set.")
        sys.exit(1)

    df = fetch(db_url, args.outbreak_percentile)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info("Training data written to %s (%d rows)", output_path, len(df))


if __name__ == "__main__":
    main()
