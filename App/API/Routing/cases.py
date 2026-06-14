"""
cases.py
--------
FastAPI router for Case lifecycle and officer-assignment endpoints.

Endpoints
---------
  POST   /cases                                      – open_case
  GET    /cases                                      – list_cases
  GET    /cases/{case_id}                            – get_case
  PATCH  /cases/{case_id}                            – update_case
  PATCH  /cases/{case_id}/close                      – close_case
  GET    /cases/{case_id}/details                    – get_case_details
  POST   /cases/{case_id}/officers/{officer_id}      – assign_officer_to_case
  DELETE /cases/{case_id}/officers/{officer_id}      – unlink_officer_from_case
"""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from App.API.deps import get_db
from App.schema.case import (
    CaseCloseRequest,
    CaseCloseResponse,
    CaseDetailResponse,
    CaseInclude,
    CaseListQuery,
    CaseListResponse,
    CaseOpenRequest,
    CaseOpenResponse,
    CaseRead,
    CaseSortBy,
    CaseStatus,
    CaseUpdateRequest,
)
from App.CRUD.case import (
    close_case,
    get_case,
    get_case_details,
    list_cases,
    open_case,
    update_case,
)
from App.CRUD.common import assign_officer_to_case, unlink_officer_from_case

router = APIRouter(tags=["cases"])


# ---------------------------------------------------------------------------
# Case lifecycle
# ---------------------------------------------------------------------------

@router.post("/cases", response_model=CaseOpenResponse, status_code=201)
def open_case_endpoint(payload: CaseOpenRequest, db=Depends(get_db)):
    """Open a new case and optionally assign an initial officer."""
    try:
        return open_case(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/cases", response_model=CaseListResponse)
def list_cases_endpoint(
    crime_type: str | None = Query(default=None),
    city: str | None = Query(default=None),
    status: CaseStatus | None = Query(default=None),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    sort: CaseSortBy = Query(default=CaseSortBy.OPEN_DATE_DESC),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db=Depends(get_db),
):
    """Return a filtered, sorted, paginated list of cases."""
    try:
        query = CaseListQuery(
            crime_type=crime_type,
            city=city,
            status=status,
            from_date=from_date,
            to_date=to_date,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        return list_cases(db, query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/cases/{case_id}", response_model=CaseRead)
def get_case_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """Fetch basic details of a single case. Defaults to the latest open_date."""
    try:
        return get_case(db, case_id, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/cases/{case_id}", response_model=CaseRead)
def update_case_endpoint(
    case_id: int,
    payload: CaseUpdateRequest,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """Partially update case fields (summary, crime_type, status, assigned officer, etc.)."""
    try:
        return update_case(db, case_id, payload, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/cases/{case_id}/close", response_model=CaseCloseResponse)
def close_case_endpoint(
    case_id: int,
    payload: CaseCloseRequest,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """Close a case by setting its status to CLOSED and recording the end date."""
    try:
        return close_case(db, case_id, payload, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/cases/{case_id}/details", response_model=CaseDetailResponse)
def get_case_details_endpoint(
    case_id: int,
    include: List[CaseInclude] = Query(default=list(CaseInclude)),
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """Return a case with all related sub-entities (evidence, suspects, victims, witnesses, trials, testimonies)."""
    try:
        return get_case_details(db, case_id, include, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Officer assignment
# ---------------------------------------------------------------------------

@router.post("/cases/{case_id}/officers/{officer_id}", status_code=200)
def assign_officer_endpoint(
    case_id: int,
    officer_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """Assign a police officer to a case (idempotent — no-op if already assigned)."""
    try:
        assign_officer_to_case(db, case_id, officer_id, open_date)
        db.commit()
        return {"detail": f"Officer {officer_id} assigned to case {case_id}."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/cases/{case_id}/officers/{officer_id}", status_code=200)
def unlink_officer_endpoint(
    case_id: int,
    officer_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """Remove an officer's assignment from a case."""
    try:
        removed = unlink_officer_from_case(db, case_id, officer_id, open_date)
        db.commit()
        if not removed:
            raise HTTPException(status_code=404, detail="Assignment not found.")
        return {"detail": f"Officer {officer_id} unlinked from case {case_id}."}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
