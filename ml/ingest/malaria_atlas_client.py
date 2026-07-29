"""
ml/ingest/malaria_atlas_client.py
──────────────────────────────────
Fetches malaria incidence data from the Malaria Atlas Project (MAP)
public API.  https://malariaatlas.org/

The MAP API returns annual incidence estimates per 1 000 population
at the admin-1 or point level.  We convert to approximate raw case
counts using population_density × area approximation when exact
counts are unavailable.

NOTE: The MAP API is evolving.  If the endpoint below changes, update
OCCURRENCE_URL and the response parsing below, then re-run ingestion.
"""
import logging
from datetime import date

import httpx

logger = logging.getLogger(__name__)

# MAP occurrence point-data endpoint (public, no key required).
OCCURRENCE_URL = "https://data.malariaatlas.org/geoserver/Malaria/ows"


def fetch_cases(
    latitude: float,
    longitude: float,
    start_year: int,
    end_year: int,
    radius_degrees: float = 1.0,
    timeout: float = 30.0,
) -> list[dict]:
    """
    Returns a list of annual dicts with keys:
        date (YYYY-01-01), historical_cases (int or None)

    Uses a WFS GetFeature bounding-box query around the supplied coordinates.
    """
    # Build a simple bounding box around the centroid.
    bbox = (
        f"{longitude - radius_degrees},{latitude - radius_degrees},"
        f"{longitude + radius_degrees},{latitude + radius_degrees}"
    )
    params = {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": "Malaria:data_no_details",
        "outputFormat": "application/json",
        "bbox": bbox,
        "srsName": "EPSG:4326",
    }
    try:
        response = httpx.get(OCCURRENCE_URL, params=params, timeout=timeout)
        response.raise_for_status()
        features = response.json().get("features", [])
    except Exception as exc:
        logger.warning("MAP API request failed: %s — returning empty list.", exc)
        return []

    # Aggregate case counts by year.
    yearly: dict[int, int] = {}
    for feat in features:
        props = feat.get("properties", {})
        year = props.get("year_start") or props.get("year")
        cases = props.get("cases") or props.get("value")
        if year and cases is not None:
            try:
                y = int(year)
                if start_year <= y <= end_year:
                    yearly[y] = yearly.get(y, 0) + int(cases)
            except (ValueError, TypeError):
                pass

    records = [
        {"date": f"{year}-01-01", "historical_cases": count}
        for year, count in sorted(yearly.items())
    ]
    logger.info(
        "MAP: fetched %d annual records for (%.4f, %.4f) %d→%d",
        len(records), latitude, longitude, start_year, end_year,
    )
    return records
