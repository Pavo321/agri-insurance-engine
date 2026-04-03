import structlog
from datetime import datetime, timezone

from payout.calculator import calculate_payout_inr
from payout.deduplication import generate_idempotency_key, is_duplicate, get_redis_client
from payout.upi_client import UPIPayoutClient, UPIStatus
from registry.models import PayoutRecord, PayoutStatus
from rules.models import TriggerEvent

log = structlog.get_logger()


async def process_payout(
    trigger_event: TriggerEvent,
    sum_insured_inr: float,
    upi_id: str,             # decrypted at call site — never stored plaintext here
    policy_id: str,
    session,
    dry_run: bool = False,
) -> PayoutRecord:
    """
    Full payout pipeline for a single trigger event:
    1. Calculate amount
    2. Deduplication check (Redis)
    3. Write queued record to DB
    4. Call UPI API
    5. Update record with result

    Args:
        dry_run: If True, skip UPI call — for simulation/testing only
    """
    event_date = trigger_event.triggered_at.date()
    idempotency_key = generate_idempotency_key(
        str(trigger_event.farm_id),
        trigger_event.rule_id,
        event_date,
    )

    # ── Step 1: Redis dedup check ──────────────────────────
    redis = get_redis_client()
    if is_duplicate(idempotency_key, redis):
        log.warning("payout.duplicate_blocked",
                    farm_id=str(trigger_event.farm_id),
                    rule_id=trigger_event.rule_id,
                    key=idempotency_key)
        raise ValueError(f"Duplicate payout blocked: {idempotency_key}")

    # ── Step 2: Calculate amount ───────────────────────────
    payout_inr = calculate_payout_inr(trigger_event, sum_insured_inr)

    # ── Step 3: Write queued record ────────────────────────
    record = PayoutRecord(
        farm_id=trigger_event.farm_id,
        farmer_id=trigger_event.farmer_id,
        policy_id=policy_id,
        rule_id=trigger_event.rule_id,
        trigger_event_id=trigger_event.event_id,
        idempotency_key=idempotency_key,
        payout_inr=payout_inr,
        status=PayoutStatus.queued,
        evidence_artifact_url=trigger_event.evidence_artifact_url,
    )
    session.add(record)
    await session.flush()   # get record.id without committing

    if dry_run:
        log.info("payout.dry_run", farm_id=str(trigger_event.farm_id), amount=payout_inr)
        record.status = PayoutStatus.queued
        return record

    # ── Step 4: Call UPI API ───────────────────────────────
    client = UPIPayoutClient()
    record.initiated_at = datetime.now(timezone.utc)
    record.status = PayoutStatus.pending

    try:
        result = await client.initiate_payout(
            reference_id=idempotency_key,
            upi_id=upi_id,
            amount_inr=payout_inr,
            remarks=f"Crop insurance: {trigger_event.event_type} {event_date}",
        )

        record.upi_reference_id = result.reference_id

        if result.status == UPIStatus.success:
            record.status = PayoutStatus.success
            record.utr_number = result.utr_number
            record.confirmed_at = datetime.now(timezone.utc)
            log.info("payout.success",
                     farm_id=str(trigger_event.farm_id),
                     amount=payout_inr,
                     utr=result.utr_number)

        elif result.status == UPIStatus.failed:
            record.status = PayoutStatus.failed
            record.failed_at = datetime.now(timezone.utc)
            record.failure_reason = result.failure_reason
            log.error("payout.failed",
                      farm_id=str(trigger_event.farm_id),
                      reason=result.failure_reason)

        # PENDING: stays in pending state, polling task handles confirmation

    except Exception as exc:
        record.status = PayoutStatus.failed
        record.failed_at = datetime.now(timezone.utc)
        record.failure_reason = str(exc)
        log.error("payout.exception", error=str(exc), farm_id=str(trigger_event.farm_id))
        raise

    return record
