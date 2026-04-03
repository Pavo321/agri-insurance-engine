from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class FarmerCreate(BaseModel):
    name: str
    phone: str
    state_code: str
    district_code: str
    aadhaar_last4: str        # only last 4 digits accepted — never full Aadhaar
    upi_id: str | None = None


class FarmerResponse(BaseModel):
    id: str
    name: str
    phone: str
    state_code: str
    district_code: str
    is_active: bool


@router.post("/farmers", response_model=FarmerResponse, status_code=201)
async def register_farmer(farmer: FarmerCreate):
    """Register a new farmer. Aadhaar is hashed before storage."""
    # TODO: implement with DB session + registry.crud
    raise HTTPException(status_code=501, detail="Phase 1 implementation pending")


@router.get("/farmers/{farmer_id}", response_model=FarmerResponse)
async def get_farmer(farmer_id: str):
    raise HTTPException(status_code=501, detail="Phase 1 implementation pending")


@router.get("/farmers")
async def list_farmers(state_code: str | None = None, page: int = 1, limit: int = 50):
    raise HTTPException(status_code=501, detail="Phase 1 implementation pending")
