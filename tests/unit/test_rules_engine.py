import uuid
from datetime import datetime, timezone

import pytest

from rules.engine import RulesEngine
from rules.models import FarmMetrics


FARM_ID = uuid.uuid4()
FARMER_ID = uuid.uuid4()
NOW = datetime.now(timezone.utc)


def make_metrics(**kwargs) -> FarmMetrics:
    defaults = dict(
        farm_id=FARM_ID,
        stat_date=NOW,
        ndvi_change_pct=None,
        rainfall_48h_mm=None,
        rainfall_14d_mm=None,
        mean_vwc_percent=None,
        modis_flood_detected=False,
    )
    defaults.update(kwargs)
    return FarmMetrics(**defaults)


@pytest.fixture
def engine():
    return RulesEngine()


class TestFloodRainTrigger:
    def test_triggers_at_200mm(self, engine):
        metrics = make_metrics(rainfall_48h_mm=200.0)
        events = engine.evaluate(metrics, FARMER_ID, set())
        rule_ids = [e.rule_id for e in events]
        assert "FLOOD_RAIN_48H" in rule_ids

    def test_does_not_trigger_at_199mm(self, engine):
        metrics = make_metrics(rainfall_48h_mm=199.9)
        events = engine.evaluate(metrics, FARMER_ID, set())
        rule_ids = [e.rule_id for e in events]
        assert "FLOOD_RAIN_48H" not in rule_ids

    def test_blocked_by_cooldown(self, engine):
        metrics = make_metrics(rainfall_48h_mm=250.0)
        events = engine.evaluate(metrics, FARMER_ID, {"FLOOD_RAIN_48H"})
        rule_ids = [e.rule_id for e in events]
        assert "FLOOD_RAIN_48H" not in rule_ids


class TestDroughtNDVITrigger:
    def test_triggers_at_minus_30_pct(self, engine):
        metrics = make_metrics(ndvi_change_pct=-0.30)
        events = engine.evaluate(metrics, FARMER_ID, set())
        rule_ids = [e.rule_id for e in events]
        assert "DROUGHT_NDVI_30" in rule_ids

    def test_does_not_trigger_at_minus_29(self, engine):
        metrics = make_metrics(ndvi_change_pct=-0.2999)
        events = engine.evaluate(metrics, FARMER_ID, set())
        rule_ids = [e.rule_id for e in events]
        assert "DROUGHT_NDVI_30" not in rule_ids

    def test_missing_ndvi_does_not_trigger(self, engine):
        metrics = make_metrics(ndvi_change_pct=None)
        events = engine.evaluate(metrics, FARMER_ID, set())
        rule_ids = [e.rule_id for e in events]
        assert "DROUGHT_NDVI_30" not in rule_ids


class TestDroughtRainfallTrigger:
    def test_triggers_at_20mm(self, engine):
        metrics = make_metrics(rainfall_14d_mm=20.0)
        events = engine.evaluate(metrics, FARMER_ID, set())
        rule_ids = [e.rule_id for e in events]
        assert "DROUGHT_RAIN_14D" in rule_ids

    def test_does_not_trigger_at_21mm(self, engine):
        metrics = make_metrics(rainfall_14d_mm=21.0)
        events = engine.evaluate(metrics, FARMER_ID, set())
        rule_ids = [e.rule_id for e in events]
        assert "DROUGHT_RAIN_14D" not in rule_ids


class TestModisFloodTrigger:
    def test_triggers_on_flood_detected(self, engine):
        metrics = make_metrics(modis_flood_detected=True)
        events = engine.evaluate(metrics, FARMER_ID, set())
        rule_ids = [e.rule_id for e in events]
        assert "FLOOD_MODIS" in rule_ids

    def test_no_trigger_without_flood(self, engine):
        metrics = make_metrics(modis_flood_detected=False)
        events = engine.evaluate(metrics, FARMER_ID, set())
        rule_ids = [e.rule_id for e in events]
        assert "FLOOD_MODIS" not in rule_ids


class TestSoilMoistureTrigger:
    def test_triggers_at_15_pct_vwc(self, engine):
        metrics = make_metrics(mean_vwc_percent=15.0)
        events = engine.evaluate(metrics, FARMER_ID, set())
        rule_ids = [e.rule_id for e in events]
        assert "DROUGHT_SOIL_VWC" in rule_ids

    def test_does_not_trigger_at_16_pct(self, engine):
        metrics = make_metrics(mean_vwc_percent=16.0)
        events = engine.evaluate(metrics, FARMER_ID, set())
        rule_ids = [e.rule_id for e in events]
        assert "DROUGHT_SOIL_VWC" not in rule_ids


class TestMultipleRules:
    def test_flood_and_drought_can_both_fire(self, engine):
        """Both flood and drought rules can fire simultaneously — both payouts should be generated."""
        metrics = make_metrics(
            rainfall_48h_mm=250.0,
            ndvi_change_pct=-0.45,
            modis_flood_detected=True,
        )
        events = engine.evaluate(metrics, FARMER_ID, set())
        rule_ids = [e.rule_id for e in events]
        assert "FLOOD_RAIN_48H" in rule_ids
        assert "FLOOD_MODIS" in rule_ids
        assert "DROUGHT_NDVI_30" in rule_ids
