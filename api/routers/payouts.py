from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/")
async def list_payouts(
    status: str | None = None,
    farm_id: str | None = None,
    page: int = 1,
    limit: int = 50,
):
    """List payout records. Filter by status (success/pending/failed) or farm."""
    raise HTTPException(status_code=501, detail="Phase 5 implementation pending")


@router.get("/{payout_id}")
async def get_payout(payout_id: str):
    """Full payout detail including UTR number and evidence artifact URL."""
    raise HTTPException(status_code=501, detail="Phase 5 implementation pending")


@router.post("/{payout_id}/retry")
async def retry_payout(payout_id: str):
    """
    Manually retry a FAILED payout.
    Re-checks deduplication before retrying.
    """
    raise HTTPException(status_code=501, detail="Phase 5 implementation pending")
