"""
ml/ingest/open_meteo_client.py
───────────────────────────────
Fetches historical daily climate data from the Open-Meteo API.
No API key required.  https://open-meteo.com/en/docs/historical-weather-api
"""
import logging
from datetime import date

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Variables we request; names match the Open-Meteo response keys.
DAILY_VARIABLES = [
    "precipitation_sum",       # maps to rainfall_mm
    "temperature_2m_mean",     # maps to avg_temp_c
    "relative_humidity_2m_mean",  # maps to humidity_pct
]


def fetch_climate(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
    timeout: float = 30.0,
) -> list[dict]:
    """
    Returns a list of daily dicts with keys:
        date, rainfall_mm, avg_temp_c, humidity_pct
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": "UTC",
    }
    response = httpx.get(BASE_URL, params=params, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    precip = daily.get("precipitation_sum", [None] * len(dates))
    temp = daily.get("temperature_2m_mean", [None] * len(dates))
    humidity = daily.get("relative_humidity_2m_mean", [None] * len(dates))

    records = []
    for i, d in enumerate(dates):
        records.append({
            "date": d,
            "rainfall_mm": precip[i],
            "avg_temp_c": temp[i],
            "humidity_pct": humidity[i],
        })

    logger.info(
        "Open-Meteo: fetched %d daily records for (%.4f, %.4f) %s→%s",
        len(records), latitude, longitude, start_date, end_date,
    )
    return records
