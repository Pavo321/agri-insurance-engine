from pathlib import Path

import yaml

from rules.models import RuleDefinition

DEFINITIONS_DIR = Path(__file__).parent / "definitions"


def load_all_rules() -> list[RuleDefinition]:
    rules = []
    for yaml_file in DEFINITIONS_DIR.glob("*.yaml"):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        if not data.get("active", True):
            continue
        rule = RuleDefinition(
            rule_id=data["rule_id"],
            name=data["name"],
            event_type=data["event_type"],
            data_source=data["data_source"],
            metric=data["condition"]["metric"],
            operator=data["condition"]["operator"],
            threshold=data["condition"]["threshold"],
            window_days=data["condition"].get("window_days", 1),
            consecutive_days=data["condition"].get("consecutive_days", 1),
            payout_tier=data["payout_tier"],
            active=data.get("active", True),
        )
        rules.append(rule)
    return rules
