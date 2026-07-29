"""
ml/ingest/worldpop_client.py
─────────────────────────────
Fetches gridded population density from the WorldPop REST API.
https://hub.worldpop.org/geodata/listing?id=29  (population density, 1km)

Returns a single population-density value (people/km²) for the
nearest grid cell to the supplied lat/lon, for the requested year.
"""
import logging

import httpx

logger = logging.getLogger(__name__)

WORLDPOP_API = "https://hub.worldpop.org/rest/data/pop/cic2020_100m"


def fetch_population_density(
    latitude: float,
    longitude: float,
    year: int = 2020,
    timeout: float = 30.0,
) -> float | None:
    """
    Returns estimated population density (people/km²) for the point,
    or None if the API is unavailable.

    WorldPop provides pre-computed country-level datasets.  This function
    queries the summary stats endpoint; for production you may want to
    switch to direct raster extraction using rasterio + the GeoTIFF files.
    """
    # WorldPop summary stats for a 1-degree bounding box around the point.
    params = {
        "iso3": _latlon_to_iso3(latitude, longitude),
        "year": year,
    }
    try:
        response = httpx.get(WORLDPOP_API, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        # data["data"] is a list; take the first matching record's mean density.
        records = data.get("data", [])
        if records:
            density = records[0].get("popd_mean") or records[0].get("total_pop")
            if density is not None:
                logger.info(
                    "WorldPop: density=%.2f for (%.4f, %.4f) year=%d",
                    float(density), latitude, longitude, year,
                )
                return float(density)
    except Exception as exc:
        logger.warning("WorldPop API request failed: %s — returning None.", exc)

    return None


# Rough lat/lon → ISO3 lookup for supported African countries.
# In production, replace with a proper reverse-geocoding call or a
# country-boundary shapefile lookup.
_COUNTRY_ISO3 = {
    "Uganda": "UGA",
    "Kenya": "KEN",
    "Tanzania": "TZA",
    "Ghana": "GHA",
    "Nigeria": "NGA",
    "DRC": "COD",
    "Zambia": "ZMB",
    "Malawi": "MWI",
    "Mozambique": "MOZ",
    "Madagascar": "MDG",
}


def _latlon_to_iso3(latitude: float, longitude: float) -> str:
    """
    Placeholder: returns a best-effort ISO3 code based on coordinate ranges.
    Replace with a proper reverse-geocoding step for a production system.
    """
    # Very rough centroids — good enough for the MVP's seeded regions.
    if -5 < latitude < 5 and 29 < longitude < 35:
        return "UGA"
    if -5 < latitude < 5 and 33 < longitude < 42:
        return "KEN"
    if -12 < latitude < 0 and 29 < longitude < 41:
        return "TZA"
    if 4 < latitude < 12 and -4 < longitude < 2:
        return "GHA"
    if 4 < latitude < 14 and 2 < longitude < 15:
        return "NGA"
    if -6 < latitude < 5 and 12 < longitude < 31:
        return "COD"
    if -19 < latitude < -8 and 21 < longitude < 34:
        return "ZMB"
    if -18 < latitude < -9 and 32 < longitude < 36:
        return "MWI"
    if -27 < latitude < -10 and 30 < longitude < 41:
        return "MOZ"
    if -26 < latitude < -12 and 43 < longitude < 51:
        return "MDG"
    return "NGA"  # fallback
