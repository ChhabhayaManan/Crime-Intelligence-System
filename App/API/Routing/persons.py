"""
persons.py
----------
FastAPI router for Address and Person CRUD endpoints.

Endpoints
---------
  POST   /addresses                     – create_address
  GET    /addresses                     – list_addresses
  GET    /addresses/{address_id}        – get_address
  PATCH  /addresses/{address_id}        – update_address

  POST   /persons                       – create_person
  GET    /persons                       – list_persons
  GET    /persons/{person_id}           – get_person
  PATCH  /persons/{person_id}           – update_person
  GET    /persons/{person_id}/cases     – get_person_cases
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from App.API.deps import get_db
from App.schema.core import (
    AddressCreate,
    AddressRead,
    AddressUpdate,
    PersonCreate,
    PersonCreateResponse,
    PersonListResponse,
    PersonRead,
    PersonRole,
    PersonUpdate,
)
from App.CRUD.person import (
    create_address,
    create_person,
    get_address,
    get_person,
    get_person_cases,
    list_addresses,
    list_persons,
    update_address,
    update_person,
)
router = APIRouter(tags=["persons"])


# ---------------------------------------------------------------------------
# Address endpoints
# ---------------------------------------------------------------------------

@router.post("/addresses", response_model=AddressRead, status_code=201)
def create_address_endpoint(payload: AddressCreate, db=Depends(get_db)):
    """Create a new address record."""
    try:
        return create_address(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/addresses", response_model=dict)
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


# ---------------------------------------------------------------------------
# Person endpoints
# ---------------------------------------------------------------------------

@router.post("/persons", response_model=PersonCreateResponse, status_code=201)
def create_person_endpoint(payload: PersonCreate, db=Depends(get_db)):
    """Create a new person (with inline or referenced address)."""
    try:
        return create_person(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/persons", response_model=PersonListResponse)
def list_persons_endpoint(
    query: str | None = Query(default=None, description="Free-text name search"),
    role: PersonRole | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db=Depends(get_db),
):
    """Paginated list of persons with optional name and role filters."""
    return list_persons(db, query=query, role=role, page=page, page_size=page_size)


@router.get("/persons/{person_id}", response_model=PersonRead)
def get_person_endpoint(person_id: int, db=Depends(get_db)):
    """Fetch full details of a person by ID, including all role profiles."""
    try:
        return get_person(db, person_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/persons/{person_id}", response_model=PersonRead)
def update_person_endpoint(person_id: int, payload: PersonUpdate, db=Depends(get_db)):
    """Partially update person details and/or their linked address."""
    try:
        return update_person(db, person_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/persons/{person_id}/cases", response_model=list[dict])
def get_person_cases_endpoint(person_id: int, db=Depends(get_db)):
    """Return all cases associated with a person, and the role(s) they hold in each."""
    try:
        return get_person_cases(db, person_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
