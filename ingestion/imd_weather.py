import structlog
from datetime import date, datetime, timezone
from typing import Generator

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings

log = structlog.get_logger()

IMD_BASE_URL = "https://api.imd.gov.in/v1"   # placeholder — replace with actual IMD endpoint


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
def fetch_station_readings(district_code: str, fetch_date: date) -> list[dict]:
    """
    Fetch hourly weather readings from IMD for a given district.

    Returns list of sensor reading dicts ready for DB insertion.
    Falls back to mock data when IMD_API_TOKEN is not configured.
    """
    if not settings.imd_api_token:
        log.warning("imd.using_mock_data", district=district_code)
        return _mock_imd_readings(district_code, fetch_date)

    headers = {"Authorization": f"Bearer {settings.imd_api_token}"}
    params = {
        "district": district_code,
        "date": fetch_date.isoformat(),
        "interval": "hourly",
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.get(f"{IMD_BASE_URL}/observations", headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    readings = []
    for obs in data.get("observations", []):
        rainfall = obs.get("rainfall_mm")
        # IMD uses -99 as missing data sentinel — treat as None
        if rainfall is not None and rainfall < 0:
            rainfall = None

        readings.append({
            "station_id": obs["station_id"],
            "timestamp": obs["timestamp"],
            "rainfall_mm": rainfall,
            "temp_celsius": obs.get("temp_c"),
            "humidity_pct": obs.get("humidity"),
            "wind_kmh": obs.get("wind_speed"),
            "source": "imd",
        })

    log.info("imd.fetched", district=district_code, count=len(readings))
    return readings


def _mock_imd_readings(district_code: str, fetch_date: date) -> list[dict]:
    """Generate realistic mock IMD data for Maharashtra (MH) for development."""
    import random
    readings = []
    for hour in range(24):
        ts = datetime(fetch_date.year, fetch_date.month, fetch_date.day, hour, 0, 0, tzinfo=timezone.utc)
        readings.append({
            "station_id": f"MH_{district_code}_01",
            "timestamp": ts.isoformat(),
            "rainfall_mm": round(random.uniform(0, 15), 2),
            "temp_celsius": round(random.uniform(22, 38), 1),
            "humidity_pct": round(random.uniform(40, 95), 1),
            "wind_kmh": round(random.uniform(5, 40), 1),
            "source": "imd_mock",
        })
    return readings
