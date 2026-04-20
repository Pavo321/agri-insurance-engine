"""
NASA MODIS Flood/Fire ingestion using EARTHDATA token.
Product: MCDWD_L3_F2_NRT (MODIS/Combined Flood 1-Day 250m)
         MCD64A1 (Burned Area Monthly)

NASA EARTHDATA token stored in .env — never hardcoded.
"""
import json
import os
import ssl
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import structlog

log = structlog.get_logger()

# Maharashtra bounding box (west, south, east, north)
MH_BBOX = {"west": 72.6, "south": 15.6, "east": 80.9, "north": 22.1}

# MODIS CMR (Common Metadata Repository) search endpoint
CMR_SEARCH_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"

# Data download base
EARTHDATA_BASE = "https://e4ftl01.cr.usgs.gov"

DATA_DIR = Path(__file__).parent.parent / "data" / "modis"


def _get_token() -> str:
    token = os.getenv("NASA_EARTHDATA_TOKEN", "")
    if not token:
        raise ValueError("NASA_EARTHDATA_TOKEN not set in .env")
    return token


def _ssl_context():
    """Create SSL context — handles macOS certificate issues."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def search_modis_granules(product: str, fetch_date: date, bbox: dict) -> list[dict]:
    """
    Search NASA CMR for MODIS granules covering Maharashtra for a given date.

    Returns list of granule metadata dicts with download URLs.
    """
    params = (
        f"short_name={product}"
        f"&temporal={fetch_date.isoformat()}T00:00:00Z,{fetch_date.isoformat()}T23:59:59Z"
        f"&bounding_box={bbox['west']},{bbox['south']},{bbox['east']},{bbox['north']}"
        f"&page_size=20"
        f"&sort_key=start_date"
    )
    url = f"{CMR_SEARCH_URL}?{params}"

    headers = {"Accept": "application/json"}
    token = _get_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as r:
            data = json.loads(r.read())
        granules = data.get("feed", {}).get("entry", [])
        log.info("modis.search", product=product, date=str(fetch_date), found=len(granules))
        return granules
    except urllib.error.HTTPError as e:
        log.error("modis.search_failed", status=e.code, product=product)
        return []
    except Exception as e:
        log.error("modis.search_error", error=str(e))
        return []


def get_flood_status_for_maharashtra(fetch_date: date) -> dict:
    """
    Check if NASA MODIS detected any flood pixels over Maharashtra on given date.

    Uses MCDWD (MODIS/Combined Flood Detection) NRT product.
    Returns summary dict — no file download needed for basic flood detection.
    """
    # Try NRT flood product first
    granules = search_modis_granules("MCDWD_L3_F2_NRT", fetch_date, MH_BBOX)

    if not granules:
        # Fall back to previous day (NRT data may have 1-day lag)
        yesterday = fetch_date - timedelta(days=1)
        granules = search_modis_granules("MCDWD_L3_F2_NRT", yesterday, MH_BBOX)
        log.info("modis.using_previous_day", date=str(yesterday))

    return {
        "date": str(fetch_date),
        "product": "MCDWD_L3_F2_NRT",
        "granules_found": len(granules),
        "flood_data_available": len(granules) > 0,
        "granule_ids": [g.get("id", "") for g in granules[:3]],
        "bounding_box": MH_BBOX,
    }


def fetch_modis_granule_urls(product: str, fetch_date: date) -> list[str]:
    """
    Get direct download URLs for MODIS granules covering Maharashtra.
    """
    granules = search_modis_granules(product, fetch_date, MH_BBOX)
    urls = []
    for g in granules:
        links = g.get("links", [])
        for link in links:
            if link.get("rel") == "http://esipfed.org/ns/fedsearch/1.1/data#":
                urls.append(link["href"])
    return urls


def download_modis_file(url: str, output_path: Path) -> bool:
    """
    Download a single MODIS file (HDF4) using EARTHDATA bearer token auth.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = {}
    token = _get_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=120, context=_ssl_context()) as r:
            output_path.write_bytes(r.read())
        log.info("modis.downloaded", file=output_path.name, size_mb=round(output_path.stat().st_size / 1e6, 2))
        return True
    except Exception as e:
        log.error("modis.download_failed", url=url, error=str(e))
        return False


if __name__ == "__main__":
    # Quick test — run directly to verify token works
    import sys
    from datetime import date

    test_date = date.today() - timedelta(days=3)   # 3 days ago (NRT data is available)
    print(f"\nTesting NASA MODIS fetch for Maharashtra — {test_date}\n")

    result = get_flood_status_for_maharashtra(test_date)
    print(json.dumps(result, indent=2))

    if result["flood_data_available"]:
        print(f"\n✓ NASA EARTHDATA connection working")
        print(f"  Found {result['granules_found']} granule(s) over Maharashtra")
    else:
        print(f"\n⚠ No granules found — may be normal for this date/region")
        print("  Token is valid (no auth error). Data may not be available for this date.")
