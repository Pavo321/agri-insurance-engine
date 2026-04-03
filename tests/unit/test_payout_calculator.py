import uuid
from datetime import datetime, timezone

import pytest

from payout.calculator import calculate_payout_inr, TIER_PAYOUT_PCT
from rules.models import TriggerEvent


def make_event(payout_tier: str) -> TriggerEvent:
    return TriggerEvent(
        rule_id="TEST_RULE",
        farm_id=uuid.uuid4(),
        farmer_id=uuid.uuid4(),
        event_type="flood",
        triggered_at=datetime.now(timezone.utc),
        metric_value=250.0,
        threshold=200.0,
        data_source="imd_weather",
        evidence_artifact_url="s3://test/tile.tif",
        payout_tier=payout_tier,
    )


class TestPayoutCalculator:
    def test_tier_1_is_40_percent(self):
        event = make_event("tier_1")
        result = calculate_payout_inr(event, sum_insured_inr=50000.0)
        assert result == 20000.0   # 40% of 50,000

    def test_tier_2_is_25_percent(self):
        event = make_event("tier_2")
        result = calculate_payout_inr(event, sum_insured_inr=50000.0)
        assert result == 12500.0   # 25% of 50,000

    def test_tier_3_is_15_percent(self):
        event = make_event("tier_3")
        result = calculate_payout_inr(event, sum_insured_inr=50000.0)
        assert result == 7500.0    # 15% of 50,000

    def test_hard_cap_at_25000(self):
        """Even with huge sum insured, payout must not exceed ₹25,000."""
        event = make_event("tier_1")
        result = calculate_payout_inr(event, sum_insured_inr=200000.0)
        assert result == 25000.0

    def test_small_policy_not_capped(self):
        """Small policy well below cap — no cap should apply."""
        event = make_event("tier_1")
        result = calculate_payout_inr(event, sum_insured_inr=10000.0)
        assert result == 4000.0    # 40% of 10,000 — well below ₹25,000 cap
