import hashlib
import hmac
import time

from fastapi import APIRouter, HTTPException, Header, Request

from config.settings import settings

router = APIRouter()

WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300   # 5-minute window to prevent replay attacks


def verify_hmac(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify HMAC-SHA256 webhook signature.
    Timing-safe comparison to prevent timing attacks.
    """
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/imd")
async def receive_imd_webhook(
    request: Request,
    x_imd_signature: str = Header(None),
    x_imd_timestamp: str = Header(None),
):
    """
    Receive push notification from IMD for extreme weather alerts.
    Verified via HMAC-SHA256 signature + 5-minute timestamp window.
    """
    if not x_imd_signature or not x_imd_timestamp:
        raise HTTPException(status_code=401, detail="Missing webhook signature headers")

    # Replay attack prevention: reject if timestamp > 5 minutes old
    try:
        ts = int(x_imd_timestamp)
        if abs(time.time() - ts) > WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS:
            raise HTTPException(status_code=401, detail="Webhook timestamp expired")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp")

    body = await request.body()
    if not verify_hmac(body, x_imd_signature, settings.imd_api_token):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # TODO: parse body, queue ingestion task via Celery
    return {"status": "accepted"}


@router.post("/upi/callback")
async def receive_upi_callback(
    request: Request,
    x_razorpay_signature: str = Header(None),
):
    """
    Receive UPI payment confirmation callback from Razorpay/NPCI.
    Updates payout_records with confirmed UTR number.
    """
    body = await request.body()
    if x_razorpay_signature:
        if not verify_hmac(body, x_razorpay_signature, settings.upi_api_key):
            raise HTTPException(status_code=401, detail="Invalid UPI callback signature")

    # TODO: parse UTR from body, update payout_records status to SUCCESS
    return {"status": "accepted"}
