"""
ml/ingest/ingest.py
────────────────────
Main ingestion script.  Fetches climate, malaria case, and population data
for all seeded regions and upserts into Postgres.

Designed to run as a GitHub Actions cron job (see .github/workflows/ingest.yml).
Idempotent: uses ON CONFLICT DO NOTHING on the unique constraint
(region_id, date, source) so re-runs never duplicate rows.

Usage:
    python ml/ingest/ingest.py
    python ml/ingest/ingest.py --days-back 30
"""
import argparse
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")

from ml.ingest.open_meteo_client import fetch_climate
from ml.ingest.malaria_atlas_client import fetch_cases
from ml.ingest.worldpop_client import fetch_population_density

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def get_session(database_url: str):
    # Normalise scheme for psycopg3
    url = database_url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    import re
    url = re.sub(r"[?&]sslmode=[^&]*", "", url).rstrip("?")
    is_neon = "neon" in database_url
    connect_args = {"sslmode": "require"} if is_neon else {}
    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    Session = sessionmaker(bind=engine)
    return Session()


def upsert_indicator(session, region_id: int, record: dict, source: str) -> None:
    """Insert a single indicator row, skipping if it already exists."""
    stmt = text("""
        INSERT INTO region_indicators
            (region_id, date, rainfall_mm, avg_temp_c, humidity_pct,
             population_density, historical_cases, source)
        VALUES
            (:region_id, :date, :rainfall_mm, :avg_temp_c, :humidity_pct,
             :population_density, :historical_cases, :source)
        ON CONFLICT (region_id, date, source) DO NOTHING
    """)
    session.execute(stmt, {
        "region_id": region_id,
        "date": record.get("date"),
        "rainfall_mm": record.get("rainfall_mm"),
        "avg_temp_c": record.get("avg_temp_c"),
        "humidity_pct": record.get("humidity_pct"),
        "population_density": record.get("population_density"),
        "historical_cases": record.get("historical_cases"),
        "source": source,
    })


def run_ingestion(database_url: str, days_back: int = 90) -> None:
    session = get_session(database_url)
    try:
        regions = session.execute(
            text("SELECT id, name, country, latitude, longitude FROM regions")
        ).fetchall()

        if not regions:
            logger.warning("No regions found in database. Run migrations first.")
            return

        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        start_year = start_date.year
        end_year = end_date.year

        total_inserted = 0

        for region in regions:
            region_id = region.id
            name = region.name
            lat, lon = region.latitude, region.longitude
            logger.info("Ingesting data for %s, %s (id=%d)…", name, region.country, region_id)

            # ── Climate data (Open-Meteo) ─────────────────────────────────
            try:
                climate_records = fetch_climate(lat, lon, start_date, end_date)
                for rec in climate_records:
                    upsert_indicator(session, region_id, rec, source="open-meteo")
                total_inserted += len(climate_records)
            except Exception as exc:
                logger.error("Climate fetch failed for %s: %s", name, exc)

            # ── Malaria case data (MAP) ───────────────────────────────────
            try:
                case_records = fetch_cases(lat, lon, start_year, end_year)
                for rec in case_records:
                    upsert_indicator(session, region_id, rec, source="malaria-atlas")
                total_inserted += len(case_records)
            except Exception as exc:
                logger.error("MAP fetch failed for %s: %s", name, exc)

            # ── Population density (WorldPop) ─────────────────────────────
            try:
                density = fetch_population_density(lat, lon, year=min(end_year, 2020))
                if density is not None:
                    # WorldPop gives a single value per region/year — store as
                    # a synthetic daily record on Jan 1 of the reference year.
                    rec = {
                        "date": f"{min(end_year, 2020)}-01-01",
                        "population_density": density,
                    }
                    upsert_indicator(session, region_id, rec, source="worldpop")
                    total_inserted += 1
            except Exception as exc:
                logger.error("WorldPop fetch failed for %s: %s", name, exc)

        session.commit()
        logger.info("Ingestion complete. ~%d rows upserted.", total_inserted)

    except Exception as exc:
        session.rollback()
        logger.error("Ingestion failed with unhandled error: %s", exc)
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest data for all seeded regions.")
    parser.add_argument(
        "--days-back",
        type=int,
        default=90,
        help="How many days of historical climate data to fetch (default: 90)",
    )
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL is not set.")
        sys.exit(1)

    run_ingestion(db_url, days_back=args.days_back)


if __name__ == "__main__":
    main()
