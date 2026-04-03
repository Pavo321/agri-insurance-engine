import numpy as np


def calculate_ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """
    Compute NDVI = (NIR - Red) / (NIR + Red).

    Handles divide-by-zero: returns NaN where NIR + Red == 0.
    Output range: -1.0 to +1.0
      > 0.6  = healthy dense vegetation
      0.3-0.6 = moderate / stressed vegetation
      0.1-0.3 = sparse / degraded vegetation
      < 0.1  = bare soil, water, or urban
    """
    red = red.astype(np.float32)
    nir = nir.astype(np.float32)

    denominator = nir + red
    ndvi = np.where(
        denominator == 0,
        np.nan,
        (nir - red) / denominator,
    )
    return ndvi.astype(np.float32)


def ndvi_percent_change(current: np.ndarray, baseline: np.ndarray) -> np.ndarray:
    """
    Compute pixel-wise percent change: (current - baseline) / |baseline|.

    Returns negative values for NDVI decline (drought signal).
    Returns NaN where baseline is 0 or NaN.

    Example: baseline=0.6, current=0.42 → change = -0.30 (30% decline)
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        change = np.where(
            (baseline == 0) | np.isnan(baseline),
            np.nan,
            (current - baseline) / np.abs(baseline),
        )
    return change.astype(np.float32)


def mean_ndvi_change(change_array: np.ndarray) -> float:
    """Return mean NDVI percent change, ignoring NaN pixels (cloud/water)."""
    valid = change_array[~np.isnan(change_array)]
    if len(valid) == 0:
        return float("nan")
    return float(np.mean(valid))
