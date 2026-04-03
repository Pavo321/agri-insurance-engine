import numpy as np
import pytest

from processing.raster.ndvi import calculate_ndvi, ndvi_percent_change, mean_ndvi_change


class TestCalculateNDVI:
    def test_healthy_vegetation(self):
        red = np.array([[0.1]], dtype=np.float32)
        nir = np.array([[0.8]], dtype=np.float32)
        result = calculate_ndvi(red, nir)
        expected = (0.8 - 0.1) / (0.8 + 0.1)
        assert abs(result[0][0] - expected) < 1e-5

    def test_range_is_negative_one_to_one(self):
        red = np.random.uniform(0, 1, (10, 10)).astype(np.float32)
        nir = np.random.uniform(0, 1, (10, 10)).astype(np.float32)
        result = calculate_ndvi(red, nir)
        valid = result[~np.isnan(result)]
        assert np.all(valid >= -1.0)
        assert np.all(valid <= 1.0)

    def test_divide_by_zero_returns_nan(self):
        red = np.array([[0.0]], dtype=np.float32)
        nir = np.array([[0.0]], dtype=np.float32)
        result = calculate_ndvi(red, nir)
        assert np.isnan(result[0][0])

    def test_bare_soil_low_ndvi(self):
        red = np.array([[0.4]], dtype=np.float32)
        nir = np.array([[0.2]], dtype=np.float32)
        result = calculate_ndvi(red, nir)
        assert result[0][0] < 0   # bare soil / water = negative NDVI


class TestNDVIPercentChange:
    def test_30_percent_decline(self):
        baseline = np.array([[0.6]], dtype=np.float32)
        current = np.array([[0.42]], dtype=np.float32)
        result = ndvi_percent_change(current, baseline)
        assert abs(result[0][0] - (-0.30)) < 1e-4

    def test_exactly_at_threshold(self):
        """Boundary: exactly -0.30 should be at threshold, not below it."""
        baseline = np.array([[0.60]], dtype=np.float32)
        current = np.array([[0.42]], dtype=np.float32)
        result = ndvi_percent_change(current, baseline)
        assert result[0][0] <= -0.30

    def test_zero_baseline_returns_nan(self):
        baseline = np.array([[0.0]], dtype=np.float32)
        current = np.array([[0.5]], dtype=np.float32)
        result = ndvi_percent_change(current, baseline)
        assert np.isnan(result[0][0])

    def test_improvement_returns_positive(self):
        baseline = np.array([[0.4]], dtype=np.float32)
        current = np.array([[0.6]], dtype=np.float32)
        result = ndvi_percent_change(current, baseline)
        assert result[0][0] > 0


class TestMeanNDVIChange:
    def test_ignores_nan_pixels(self):
        arr = np.array([[-0.3, float("nan"), -0.4, float("nan")]])
        result = mean_ndvi_change(arr)
        assert abs(result - (-0.35)) < 1e-5

    def test_all_nan_returns_nan(self):
        arr = np.array([[float("nan"), float("nan")]])
        result = mean_ndvi_change(arr)
        assert result != result   # NaN != NaN
