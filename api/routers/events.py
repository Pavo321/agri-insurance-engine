from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/")
async def list_events(
    state_code: str | None = None,
    rule_id: str | None = None,
    page: int = 1,
    limit: int = 50,
):
    """Paginated event log. Filterable by state and rule."""
    raise HTTPException(status_code=501, detail="Phase 4 implementation pending")


@router.get("/{event_id}")
async def get_event(event_id: str):
    """Single event with full evidence chain (satellite URL, metric values)."""
    raise HTTPException(status_code=501, detail="Phase 4 implementation pending")


@router.post("/simulate")
async def simulate_event(farm_id: str, rule_id: str):
    """
    Dry-run: evaluate a rule against a specific farm.
    Returns TriggerEvent if rule would fire — does NOT initiate any payout.
    Admin only.
    """
    raise HTTPException(status_code=501, detail="Phase 4 implementation pending")
