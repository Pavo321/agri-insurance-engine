import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class RuleDefinition:
    rule_id: str
    name: str
    event_type: Literal["drought", "flood"]
    data_source: str
    metric: str
    operator: Literal["<=", ">=", "<", ">", "=="]
    threshold: float
    window_days: int = 1
    consecutive_days: int = 1
    payout_tier: Literal["tier_1", "tier_2", "tier_3"] = "tier_2"
    active: bool = True


@dataclass
class TriggerEvent:
    rule_id: str
    farm_id: uuid.UUID
    farmer_id: uuid.UUID
    event_type: str
    triggered_at: datetime
    metric_value: float
    threshold: float
    data_source: str
    evidence_artifact_url: str
    payout_tier: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class FarmMetrics:
    farm_id: uuid.UUID
    stat_date: datetime
    ndvi_change_pct: float | None = None
    rainfall_48h_mm: float | None = None
    rainfall_14d_mm: float | None = None
    mean_vwc_percent: float | None = None
    modis_flood_detected: bool = False
    modis_fire_detected: bool = False
