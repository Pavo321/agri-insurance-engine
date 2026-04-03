"""
MODIS NDVI ingestion using NASA EARTHDATA token.
Product: MOD13A2 — MODIS/Terra Vegetation Indices 16-Day L3 Global 1km

This replaces ISRO Bhuvan NDVI (which requires 24-hour expiring tokens
and only provides location services, not raster NDVI data).

NASA MODIS provides identical NDVI data at 1km resolution, 16-day composites,
free with permanent token via urs.earthdata.nasa.gov.
"""
import json
import os
import ssl
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import structlog

log = structlog.get_logger()

# Maharashtra bounding box
MH_BBOX = {"west": 72.6, "south": 15.6, "east": 80.9, "north": 22.1}

# MODIS NDVI product: 16-day composite, 1km resolution
NDVI_PRODUCT = "MOD13A2"

# CMR search endpoint
CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"

DATA_DIR = Path(__file__).parent.parent / "data" / "ndvi"


def _get_token() -> str:
    token = os.getenv("NASA_EARTHDATA_TOKEN", "")
    if not token:
        raise ValueError("NASA_EARTHDATA_TOKEN not set in .env")
    return token


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def search_ndvi_granules(start_date: date, end_date: date) -> list[dict]:
    """
    Search for MODIS NDVI granules covering Maharashtra.
    MOD13A2 is a 16-day composite — returns most recent composite in date range.
    """
    params = (
        f"short_name={NDVI_PRODUCT}"
        f"&temporal={start_date.isoformat()}T00:00:00Z,{end_date.isoformat()}T23:59:59Z"
        f"&bounding_box={MH_BBOX['west']},{MH_BBOX['south']},{MH_BBOX['east']},{MH_BBOX['north']}"
        f"&page_size=20"
        f"&sort_key=-start_date"   # most recent first
    )
    url = f"{CMR_URL}?{params}"

    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/json",
    })

    with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx()) as r:
        data = json.loads(r.read())

    granules = data.get("feed", {}).get("entry", [])
    log.info("ndvi.search", product=NDVI_PRODUCT, found=len(granules),
             start=str(start_date), end=str(end_date))
    return granules


def get_ndvi_download_urls(granules: list[dict]) -> list[dict]:
    """
    Extract HDF download URLs from granule metadata.
    Returns list of {title, date, url} dicts.
    """
    results = []
    for g in granules:
        links = g.get("links", [])
        for link in links:
            if "data#" in link.get("rel", "") and link["href"].endswith(".hdf"):
                results.append({
                    "title": g.get("title", ""),
                    "date": g.get("time_start", "")[:10],
                    "url": link["href"],
                    "granule_id": g.get("id", ""),
                })
                break
    return results


def fetch_latest_ndvi_for_maharashtra() -> dict:
    """
    Fetch the most recent MODIS NDVI granule metadata for Maharashtra.
    Returns summary with download URLs — ready to pass to GDAL processor.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=20)   # 16-day composites, look back 20 days

    granules = search_ndvi_granules(start_date, end_date)
    download_info = get_ndvi_download_urls(granules)

    return {
        "product": NDVI_PRODUCT,
        "description": "MODIS/Terra Vegetation Indices 16-Day 1km (NDVI)",
        "date_range": f"{start_date} to {end_date}",
        "granules_found": len(granules),
        "tiles_over_maharashtra": len(download_info),
        "tiles": download_info,
        "ndvi_band": "NDVI",
        "resolution_km": 1,
        "data_available": len(download_info) > 0,
    }


if __name__ == "__main__":
    print("\nFetching MODIS NDVI data for Maharashtra...\n")
    result = fetch_latest_ndvi_for_maharashtra()

    print(f"Product:    {result['product']} — {result['description']}")
    print(f"Period:     {result['date_range']}")
    print(f"Granules:   {result['granules_found']} found")
    print(f"MH Tiles:   {result['tiles_over_maharashtra']} tiles covering Maharashtra")
    print(f"Resolution: {result['resolution_km']} km per pixel")

    if result["tiles"]:
        print(f"\nSample tiles:")
        for t in result["tiles"][:4]:
            print(f"  [{t['date']}] {t['title']}")
            print(f"           {t['url'][:80]}...")

    print(f"\n{'✓ NDVI data available' if result['data_available'] else '✗ No data found'}")
