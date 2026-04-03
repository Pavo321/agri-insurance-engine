import httpx
from dataclasses import dataclass
from enum import Enum

from config.settings import settings


class UPIStatus(str, Enum):
    pending = "PENDING"
    success = "SUCCESS"
    failed = "FAILED"


@dataclass
class PayoutResult:
    reference_id: str
    status: UPIStatus
    utr_number: str | None = None
    failure_reason: str | None = None


class UPIPayoutClient:
    """
    Wrapper around Razorpay Payout API (sandbox-compatible).
    In production, swap base_url to NPCI UPI AutoPay endpoint.
    """

    def __init__(self):
        self.base_url = settings.upi_api_base_url
        self.merchant_id = settings.upi_merchant_id
        self.headers = {
            "Content-Type": "application/json",
            "X-Merchant-ID": self.merchant_id,
        }

    async def initiate_payout(
        self,
        reference_id: str,
        upi_id: str,
        amount_inr: float,
        remarks: str,
    ) -> PayoutResult:
        """
        Initiate a UPI payout to a farmer's UPI ID.
        Uses reference_id as idempotency key — NPCI deduplicates on their side too.
        """
        payload = {
            "account_number": self.merchant_id,
            "amount": int(amount_inr * 100),        # convert to paise
            "currency": "INR",
            "mode": "UPI",
            "purpose": "payout",
            "fund_account": {
                "account_type": "vpa",
                "vpa": {"address": upi_id},
            },
            "queue_if_low_balance": True,
            "reference_id": reference_id,
            "narration": remarks[:30],              # UPI narration limit
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/payouts",
                json=payload,
                headers=self.headers,
                auth=(settings.upi_api_key, ""),
            )
            response.raise_for_status()
            data = response.json()

        status_map = {
            "processing": UPIStatus.pending,
            "queued": UPIStatus.pending,
            "processed": UPIStatus.success,
            "reversed": UPIStatus.failed,
            "cancelled": UPIStatus.failed,
        }

        return PayoutResult(
            reference_id=reference_id,
            status=status_map.get(data.get("status", ""), UPIStatus.pending),
            utr_number=data.get("utr"),
            failure_reason=data.get("error", {}).get("description"),
        )

    async def check_status(self, payout_id: str) -> PayoutResult:
        """Poll status of a PENDING payout."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/payouts/{payout_id}",
                headers=self.headers,
                auth=(settings.upi_api_key, ""),
            )
            response.raise_for_status()
            data = response.json()

        status_map = {
            "processed": UPIStatus.success,
            "processing": UPIStatus.pending,
            "queued": UPIStatus.pending,
            "reversed": UPIStatus.failed,
            "cancelled": UPIStatus.failed,
        }

        return PayoutResult(
            reference_id=payout_id,
            status=status_map.get(data.get("status", ""), UPIStatus.pending),
            utr_number=data.get("utr"),
        )
