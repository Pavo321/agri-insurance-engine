import structlog

from workers.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def dispatch_payout(self, trigger_event_dict: dict):
    """
    Process a single payout for a TriggerEvent.
    Chain: dedup → calculate → UPI call → ledger write
    Phase 5 implementation.
    """
    log.info("payout.dispatch.received",
             rule_id=trigger_event_dict.get("rule_id"),
             farm_id=trigger_event_dict.get("farm_id"))
    # Phase 5: implement full payout pipeline
    # from payout.pipeline import process_payout
    log.info("payout.dispatch.stub", note="Phase 5 implementation pending")


@celery_app.task(bind=True)
def poll_pending_payouts(self):
    """
    Every 10 minutes: check PENDING payouts and update status from UPI API.
    If confirmed → mark SUCCESS + record UTR.
    If > 4 hours PENDING → mark FAILED + alert.
    Phase 5 implementation.
    """
    log.info("payout.poll.stub", note="Phase 5 implementation pending")
