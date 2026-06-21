"""
persons.py
----------
FastAPI router for Person CRUD endpoints.

Endpoints
---------
  POST   /persons                       – create_person
  GET    /persons                       – list_persons
  GET    /persons/{person_id}           – get_person
  PATCH  /persons/{person_id}           – update_person
  GET    /persons/{person_id}/cases     – get_person_cases
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from App.API.deps import get_db
from App.schema.core import (
    PersonCreate,
    PersonCreateResponse,
    PersonListResponse,
    PersonRead,
    PersonRole,
    PersonUpdate,
)
from App.CRUD.person import (
    create_person,
    get_person,
    get_person_cases,
    list_persons,
    update_person,
)

router = APIRouter(tags=["persons"])


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
