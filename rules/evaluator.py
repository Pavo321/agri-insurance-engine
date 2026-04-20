"""
Full rules evaluator — wires Open-Meteo rainfall + NASA MODIS NDVI
into the parametric trigger rules engine.

Runs hourly via Celery Beat. For each district:
1. Fetch live rainfall from Open-Meteo
2. Fetch NDVI stats from NASA MODIS pipeline
3. Evaluate all 5 YAML rules
4. Return list of TriggerEvents
"""
import uuid
from datetime import datetime, timezone

import structlog

from ingestion.open_meteo import fetch_district_rainfall, MAHARASHTRA_DISTRICTS
from ingestion.modis_flood import get_flood_status_for_maharashtra
from processing.raster.ndvi_pipeline import get_maharashtra_ndvi_report
from rules.loader import load_all_rules
from rules.models import FarmMetrics, TriggerEvent

log = structlog.get_logger()

# Payout tier percentages
TIER_PCT = {"tier_1": 0.40, "tier_2": 0.25, "tier_3": 0.15}

# Hard cap per event
MAX_PAYOUT_INR = 25000.0


def evaluate_district(district: str, lat: float, lon: float,
                       ndvi_stats: dict, flood_data: dict) -> list[dict]:
    """
    Evaluate all trigger rules for a single district.
    Returns list of trigger result dicts.
    """
    rules = load_all_rules()
    triggers = []
    now = datetime.now(timezone.utc)

    # Fetch live rainfall
    weather = fetch_district_rainfall(district, lat, lon, past_days=14)

    # Build FarmMetrics from real data
    ndvi_district = ndvi_stats.get(district, {})
    metrics = FarmMetrics(
        farm_id=uuid.uuid4(),   # placeholder — real run uses actual farm IDs
        stat_date=now,
        ndvi_change_pct=ndvi_district.get("ndvi_change_pct"),
        rainfall_48h_mm=weather["rainfall_48h_mm"],
        rainfall_14d_mm=weather["rainfall_14d_mm"],
        mean_vwc_percent=None,   # soil sensors not deployed in pilot
        modis_flood_detected=flood_data.get("flood_data_available", False),
    )

    # Evaluate each rule
    import operator as op
    OPS = {"<=": op.le, ">=": op.ge, "<": op.lt, ">": op.gt}
    METRIC_MAP = {
        "ndvi_change_pct": metrics.ndvi_change_pct,
        "cumulative_rainfall_mm_48h": metrics.rainfall_48h_mm,
        "cumulative_rainfall_mm_14d": metrics.rainfall_14d_mm,
        "vwc_percent": metrics.mean_vwc_percent,
        "modis_flood": 1.0 if metrics.modis_flood_detected else 0.0,
    }

    for rule in rules:
        value = METRIC_MAP.get(rule.metric)
        if value is None:
            continue
        compare = OPS.get(rule.operator)
        if compare and compare(value, rule.threshold):
            payout_pct = TIER_PCT.get(rule.payout_tier, 0.15)
            # Example: sum insured ₹60,000 — real system reads from policy DB
            sample_sum_insured = 60000.0
            payout_inr = min(sample_sum_insured * payout_pct, MAX_PAYOUT_INR)

            triggers.append({
                "district": district,
                "rule_id": rule.rule_id,
                "event_type": rule.event_type,
                "metric": rule.metric,
                "value": round(value, 4),
                "threshold": rule.threshold,
                "payout_tier": rule.payout_tier,
                "payout_pct": f"{payout_pct*100:.0f}%",
                "sample_payout_inr": payout_inr,
                "triggered_at": now.isoformat(),
                "data_source": rule.data_source,
            })
            log.info("rule.triggered",
                     district=district,
                     rule=rule.rule_id,
                     value=value,
                     threshold=rule.threshold,
                     payout=payout_inr)

    return triggers


def run_full_evaluation() -> dict:
    """
    Run full trigger evaluation for all Maharashtra districts.
    Returns complete report of all triggered events.
    """
    from datetime import date, timedelta

    log.info("evaluation.start", districts=len(MAHARASHTRA_DISTRICTS))

    # Fetch shared data once (not per district)
    ndvi_report = get_maharashtra_ndvi_report()
    ndvi_stats = ndvi_report["districts"]
    flood_data = get_flood_status_for_maharashtra(date.today() - timedelta(days=2))

    all_triggers = []
    district_summary = []

    for district, (lat, lon) in MAHARASHTRA_DISTRICTS.items():
        triggers = evaluate_district(district, lat, lon, ndvi_stats, flood_data)
        all_triggers.extend(triggers)

        weather = fetch_district_rainfall(district, lat, lon)
        district_summary.append({
            "district": district,
            "rainfall_14d_mm": weather["rainfall_14d_mm"],
            "rainfall_48h_mm": weather["rainfall_48h_mm"],
            "ndvi_change_pct": ndvi_stats.get(district, {}).get("ndvi_change_pct"),
            "triggers_fired": len(triggers),
            "rules_triggered": [t["rule_id"] for t in triggers],
        })

    return {
        "evaluation_time": datetime.now(timezone.utc).isoformat(),
        "total_districts": len(MAHARASHTRA_DISTRICTS),
        "total_triggers": len(all_triggers),
        "triggers": all_triggers,
        "district_summary": district_summary,
        "data_sources": ["Open-Meteo (rainfall)", "NASA MODIS (NDVI + flood)"],
    }


if __name__ == "__main__":
    print("\nRunning full trigger evaluation — Maharashtra\n")
    result = run_full_evaluation()

    print(f"Districts evaluated: {result['total_districts']}")
    print(f"Total triggers fired: {result['total_triggers']}")
    print(f"Data sources: {', '.join(result['data_sources'])}")

    if result["triggers"]:
        print(f"\n{'District':<15} {'Rule':<22} {'Value':>10} {'Threshold':>10} {'Payout':>12}")
        print("-" * 75)
        for t in result["triggers"]:
            print(f"{t['district']:<15} {t['rule_id']:<22} {t['value']:>10} "
                  f"{t['threshold']:>10} ₹{t['sample_payout_inr']:>10,.0f}")
    else:
        print("\nNo triggers fired — all districts within normal thresholds")

    print(f"\nDistrict Summary:")
    print(f"{'District':<15} {'14d Rain':>10} {'48h Rain':>10} {'NDVI Chg':>10} {'Triggers':>10}")
    print("-" * 60)
    for d in result["district_summary"]:
        ndvi = f"{d['ndvi_change_pct']*100:.1f}%" if d['ndvi_change_pct'] else "N/A"
        print(f"{d['district']:<15} {d['rainfall_14d_mm']:>9.1f}mm {d['rainfall_48h_mm']:>9.1f}mm "
              f"{ndvi:>10} {d['triggers_fired']:>10}")
