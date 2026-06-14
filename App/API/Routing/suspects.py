"""
suspects.py
-----------
FastAPI router for Suspect CRUD endpoints.

Endpoints
---------
  POST   /cases/{case_id}/suspects                   – add_case_suspect
  GET    /cases/{case_id}/suspects                   – list_case_suspects
  PATCH  /cases/{case_id}/suspects/{suspect_id}      – update_case_suspect
  GET    /suspects/{suspect_id}                      – get_suspect
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from App.API.deps import get_db
from App.schema.case import (
    CaseSuspectCreateRequest,
    CaseSuspectCreateResponse,
    CaseSuspectListResponse,
    CaseSuspectUpdateRequest,
    CaseSuspectUpdateResponse,
    SuspectRead,
)
from App.CRUD.suspect import (
    add_case_suspect,
    get_suspect,
    list_case_suspects,
    update_case_suspect,
)
router = APIRouter(tags=["suspects"])


@router.post("/cases/{case_id}/suspects", response_model=CaseSuspectCreateResponse, status_code=201)
def add_suspect_endpoint(
    case_id: int,
    payload: CaseSuspectCreateRequest,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """Add a suspect to a case (by existing person_id or inline new person) and link evidence."""
    try:
        return add_case_suspect(db, case_id, payload, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/cases/{case_id}/suspects", response_model=CaseSuspectListResponse)
def list_suspects_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """List all suspects linked to a case."""
    try:
        return list_case_suspects(db, case_id, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch(
    "/cases/{case_id}/suspects/{suspect_id}",
    response_model=CaseSuspectUpdateResponse,
)
def update_suspect_endpoint(
    case_id: int,
    suspect_id: int,
    payload: CaseSuspectUpdateRequest,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """Update a suspect's arrest status, physical description, or bail information."""
    try:
        return update_case_suspect(db, case_id, suspect_id, payload, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/suspects/{suspect_id}", response_model=SuspectRead)
def get_suspect_endpoint(suspect_id: int, db=Depends(get_db)):
    """Fetch a suspect's profile by their person ID."""
    try:
        return get_suspect(db, suspect_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
