"""
Zonal statistics fallback using rasterstats.
Used in development and for small batches (single district).
For full-state production runs, use spark_overlay.py instead.
"""
from pathlib import Path

import numpy as np
from rasterstats import zonal_stats


def compute_farm_ndvi_stats(
    farm_geojson: dict,
    ndvi_raster_path: Path,
) -> dict:
    """
    Compute mean, min, max NDVI for a single farm polygon.

    Args:
        farm_geojson: GeoJSON Feature with polygon geometry (EPSG:4326)
        ndvi_raster_path: Path to NDVI GeoTIFF

    Returns:
        dict with mean_ndvi, min_ndvi, max_ndvi, valid_pixel_count
    """
    stats = zonal_stats(
        farm_geojson,
        str(ndvi_raster_path),
        stats=["mean", "min", "max", "count"],
        nodata=np.nan,
        geojson_out=False,
    )

    if not stats or stats[0] is None:
        return {"mean_ndvi": None, "min_ndvi": None, "max_ndvi": None, "valid_pixel_count": 0}

    result = stats[0]
    return {
        "mean_ndvi": result.get("mean"),
        "min_ndvi": result.get("min"),
        "max_ndvi": result.get("max"),
        "valid_pixel_count": result.get("count", 0),
    }


def batch_farm_stats(
    farms: list[dict],          # list of GeoJSON Features
    ndvi_raster_path: Path,
    change_raster_path: Path,
) -> list[dict]:
    """
    Compute NDVI and NDVI-change stats for a batch of farms.
    Returns list of stat dicts in same order as input farms.
    """
    ndvi_stats = zonal_stats(
        farms,
        str(ndvi_raster_path),
        stats=["mean"],
        nodata=np.nan,
    )
    change_stats = zonal_stats(
        farms,
        str(change_raster_path),
        stats=["mean"],
        nodata=np.nan,
    )

    results = []
    for ndvi_s, change_s in zip(ndvi_stats, change_stats):
        results.append({
            "mean_ndvi": ndvi_s.get("mean") if ndvi_s else None,
            "ndvi_change_pct": change_s.get("mean") if change_s else None,
        })
    return results
