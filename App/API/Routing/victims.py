"""
victims.py
----------
FastAPI router for Victim endpoints.

Endpoints
---------
  POST   /cases/{case_id}/victims    – add_case_victim
  GET    /cases/{case_id}/victims    – list_case_victims
  GET    /victims                    – list_victims  (global)
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from App.API.deps import get_db
from App.schema.case import (
    CaseVictimCreateRequest,
    CaseVictimCreateResponse,
    CaseVictimListResponse,
    VictimListResponse,
    VictimRead,
)
from App.CRUD.victim import (
    add_case_victim,
    list_case_victims,
    list_victims,
)
router = APIRouter(tags=["victims"])


@router.post("/cases/{case_id}/victims", response_model=CaseVictimCreateResponse, status_code=201)
def add_victim_endpoint(
    case_id: int,
    payload: CaseVictimCreateRequest,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """Add a victim to a case (by existing person_id or inline new person)."""
    try:
        return add_case_victim(db, case_id, payload, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/cases/{case_id}/victims", response_model=CaseVictimListResponse)
def list_case_victims_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """List all victims affected by a given case."""
    try:
        return list_case_victims(db, case_id, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/victims", response_model=VictimListResponse)
def list_victims_endpoint(
    query: str | None = Query(default=None, description="Free-text name search"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db=Depends(get_db),
):
    """Global paginated list of all victims with optional name filter."""
    return list_victims(db, query=query, page=page, page_size=page_size)
