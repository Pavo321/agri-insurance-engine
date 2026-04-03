import structlog

from workers.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3)
def evaluate_all_farms(self):
    """
    Hourly task: evaluate all 5 parametric rules against every active farm in Maharashtra.
    For each TriggerEvent generated → dispatch_payout.delay()
    Phase 4 implementation.
    """
    log.info("rules.evaluate.start", state="MH")
    # Phase 4: implement rules engine evaluation loop
    # from rules.engine import RulesEngine
    # engine = RulesEngine()
    # for farm in active_farms:
    #     metrics = get_farm_daily_stats(farm.id)
    #     recent_rule_ids = get_recent_payout_rule_ids(farm.id, cooldown_days=30)
    #     events = engine.evaluate(metrics, farm.farmer_id, recent_rule_ids)
    #     for event in events:
    #         dispatch_payout.delay(event.__dict__)
    log.info("rules.evaluate.stub", note="Phase 4 implementation pending")
    return {"status": "stub"}
