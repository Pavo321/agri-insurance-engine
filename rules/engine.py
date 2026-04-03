import operator as op
from datetime import datetime, timezone

from rules.loader import load_all_rules
from rules.models import FarmMetrics, RuleDefinition, TriggerEvent

OPERATORS = {
    "<=": op.le,
    ">=": op.ge,
    "<":  op.lt,
    ">":  op.gt,
    "==": op.eq,
}

METRIC_MAP = {
    "ndvi_change_pct":      lambda m: m.ndvi_change_pct,
    "cumulative_rainfall_mm_48h": lambda m: m.rainfall_48h_mm,
    "cumulative_rainfall_mm_14d": lambda m: m.rainfall_14d_mm,
    "vwc_percent":          lambda m: m.mean_vwc_percent,
    "modis_flood":          lambda m: 1.0 if m.modis_flood_detected else 0.0,
}


class RulesEngine:
    def __init__(self):
        self.rules: list[RuleDefinition] = load_all_rules()

    def evaluate(self, metrics: FarmMetrics, farmer_id, recent_payout_rule_ids: set[str]) -> list[TriggerEvent]:
        """
        Evaluate all active rules against a farm's daily metrics.

        Args:
            metrics: Farm's computed stats for the day
            farmer_id: UUID of the farmer who owns this farm
            recent_payout_rule_ids: Set of rule_ids paid out within cooldown window (30 days)
                                    — passed in from payout_records query to enforce cooldown

        Returns:
            List of TriggerEvents. Empty list = no triggers.
        """
        events = []

        for rule in self.rules:
            # Skip if farm is in cooldown for this rule
            if rule.rule_id in recent_payout_rule_ids:
                continue

            metric_fn = METRIC_MAP.get(rule.metric)
            if metric_fn is None:
                continue

            value = metric_fn(metrics)
            if value is None:
                continue

            compare = OPERATORS[rule.operator]
            if compare(value, rule.threshold):
                events.append(TriggerEvent(
                    rule_id=rule.rule_id,
                    farm_id=metrics.farm_id,
                    farmer_id=farmer_id,
                    event_type=rule.event_type,
                    triggered_at=datetime.now(timezone.utc),
                    metric_value=value,
                    threshold=rule.threshold,
                    data_source=rule.data_source,
                    evidence_artifact_url="",   # filled by caller with S3 URL
                    payout_tier=rule.payout_tier,
                ))

        return events
