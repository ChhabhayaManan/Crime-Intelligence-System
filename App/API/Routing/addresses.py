"""
addresses.py
------------
FastAPI router for Address CRUD endpoints.

Endpoints
---------
  POST   /addresses                  – create_address
  GET    /addresses                  – list_addresses
  GET    /addresses/{address_id}     – get_address
  PATCH  /addresses/{address_id}     – update_address
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from App.API.deps import get_db
from App.schema.core import AddressCreate, AddressListResponse, AddressRead, AddressUpdate
from App.CRUD.person import create_address, get_address, list_addresses, update_address

router = APIRouter(tags=["addresses"])


@router.post("/addresses", response_model=AddressRead, status_code=201)
def create_address_endpoint(payload: AddressCreate, db=Depends(get_db)):
    """Create a new address record."""
    try:
        return create_address(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/addresses", response_model=AddressListResponse)
def list_addresses_endpoint(
    city: str | None = Query(default=None),
    country: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db=Depends(get_db),
):
    """Return a paginated list of addresses with optional city/country filters."""
    return list_addresses(db, city=city, country=country, page=page, page_size=page_size)


@router.get("/addresses/{address_id}", response_model=AddressRead)
def get_address_endpoint(address_id: int, db=Depends(get_db)):
    """Fetch a single address by ID."""
    try:
        return get_address(db, address_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/addresses/{address_id}", response_model=AddressRead)
def update_address_endpoint(address_id: int, payload: AddressUpdate, db=Depends(get_db)):
    """Partially update an address record."""
    try:
        return update_address(db, address_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
