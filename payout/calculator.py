from config.settings import settings
from rules.models import TriggerEvent

TIER_PAYOUT_PCT = {
    "tier_1": 0.40,   # 40% — severe flood
    "tier_2": 0.25,   # 25% — moderate drought
    "tier_3": 0.15,   # 15% — early warning / soil moisture
}


def calculate_payout_inr(trigger_event: TriggerEvent, sum_insured_inr: float) -> float:
    """
    Calculate payout amount from trigger event and policy sum insured.

    Formula: payout = sum_insured × tier_pct
    Hard cap: settings.max_payout_per_event_inr (default ₹25,000)
    """
    tier_pct = TIER_PAYOUT_PCT.get(trigger_event.payout_tier, 0.15)
    payout = sum_insured_inr * tier_pct
    return min(payout, settings.max_payout_per_event_inr)
