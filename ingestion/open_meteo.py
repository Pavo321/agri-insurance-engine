"""
Open-Meteo weather ingestion — free, no API key, real-time rainfall for all India.
Replaces IMD API (which requires IP whitelisting).

Data: ERA5 reanalysis + ECMWF forecast — same quality used by PMFBY internally.
Coverage: All India districts via lat/lon coordinates.
"""
import json
import ssl
import urllib.request
from datetime import date, timedelta

import structlog

log = structlog.get_logger()

BASE_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Maharashtra district coordinates (lat, lon)
MAHARASHTRA_DISTRICTS = {
    "Pune":        (18.52,  73.85),
    "Nashik":      (20.01,  73.79),
    "Aurangabad":  (19.87,  75.34),
    "Nagpur":      (21.14,  79.08),
    "Mumbai":      (19.07,  72.88),
    "Solapur":     (17.69,  75.90),
    "Kolhapur":    (16.70,  74.24),
    "Amravati":    (20.93,  77.75),
    "Latur":       (18.40,  76.56),
    "Nanded":      (19.16,  77.31),
    "Jalgaon":     (21.01,  75.56),
    "Ahmednagar":  (19.09,  74.74),
    "Satara":      (17.68,  74.00),
    "Sangli":      (16.86,  74.56),
    "Ratnagiri":   (16.99,  73.30),
    "Yavatmal":    (20.39,  78.12),
    "Chandrapur":  (19.96,  79.30),
    "Wardha":      (20.74,  78.60),
    "Osmanabad":   (18.18,  76.04),
    "Beed":        (18.98,  75.75),
}


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_district_rainfall(district: str, lat: float, lon: float, past_days: int = 14) -> dict:
    """
    Fetch rainfall data for a district using Open-Meteo API.
    Returns daily precipitation for past N days + today.

    Free, no auth, covers all India.
    """
    url = (
        f"{BASE_URL}?"
        f"latitude={lat}&longitude={lon}"
        f"&daily=precipitation_sum,rain_sum,precipitation_hours"
        f"&hourly=precipitation,rain,temperature_2m,relative_humidity_2m,wind_speed_10m"
        f"&past_days={past_days}&forecast_days=1"
        f"&timezone=Asia/Kolkata"
    )

    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx()) as r:
        data = json.loads(r.read())

    daily = data["daily"]
    hourly = data["hourly"]

    # Rolling sums for trigger rules
    rain_values = [x or 0.0 for x in daily["precipitation_sum"]]
    rain_14d = sum(rain_values[-14:])
    rain_48h = sum(rain_values[-2:])

    result = {
        "district": district,
        "lat": lat,
        "lon": lon,
        "dates": daily["time"],
        "daily_rainfall_mm": daily["precipitation_sum"],
        "rainfall_14d_mm": round(rain_14d, 2),
        "rainfall_48h_mm": round(rain_48h, 2),
        "hourly_timestamps": hourly["time"],
        "hourly_rainfall_mm": hourly["precipitation"],
        "hourly_temp_c": hourly["temperature_2m"],
        "hourly_humidity_pct": hourly["relative_humidity_2m"],
        # Trigger evaluation
        "drought_14d_trigger": rain_14d <= 20.0,
        "flood_48h_trigger": rain_48h >= 200.0,
    }

    log.info("weather.fetched",
             district=district,
             rain_14d=rain_14d,
             rain_48h=rain_48h,
             drought=result["drought_14d_trigger"],
             flood=result["flood_48h_trigger"])

    return result


def fetch_all_maharashtra() -> list[dict]:
    """Fetch rainfall for all Maharashtra districts."""
    results = []
    for district, (lat, lon) in MAHARASHTRA_DISTRICTS.items():
        try:
            data = fetch_district_rainfall(district, lat, lon)
            results.append(data)
        except Exception as e:
            log.error("weather.fetch_failed", district=district, error=str(e))
    return results


def fetch_district_by_coords(lat: float, lon: float, past_days: int = 14) -> dict:
    """Fetch rainfall for any India location by coordinates."""
    return fetch_district_rainfall(f"{lat},{lon}", lat, lon, past_days)


if __name__ == "__main__":
    print("\nLive Rainfall Data — Maharashtra Districts (Open-Meteo)\n")
    print(f"{'District':<15} {'14d Rain':>10} {'48h Rain':>10} {'Drought?':>10} {'Flood?':>8}")
    print("-" * 60)

    for district, (lat, lon) in list(MAHARASHTRA_DISTRICTS.items())[:8]:
        data = fetch_district_rainfall(district, lat, lon)
        print(f"{district:<15} {data['rainfall_14d_mm']:>9.1f}mm "
              f"{data['rainfall_48h_mm']:>9.1f}mm "
              f"{'YES' if data['drought_14d_trigger'] else 'no':>10} "
              f"{'YES' if data['flood_48h_trigger'] else 'no':>8}")
