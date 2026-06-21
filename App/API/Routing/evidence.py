"""
evidence.py
-----------
FastAPI router for Evidence CRUD endpoints (case-scoped).

Endpoints
---------
  POST   /cases/{case_id}/evidence              – add_case_evidence
  GET    /cases/{case_id}/evidence              – list_case_evidence
  GET    /evidence/{evidence_id}                – get_evidence
  PATCH  /evidence/{evidence_id}                – update_evidence
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from App.API.deps import get_db
from App.schema.case import (
    CaseEvidenceCreateRequest,
    CaseEvidenceCreateResponse,
    CaseEvidenceListResponse,
    EvidenceRead,
)
from App.CRUD.evidence import (
    add_case_evidence,
    get_evidence,
    list_case_evidence,
    update_evidence,
)
router = APIRouter(tags=["evidence"])


@router.post("/cases/{case_id}/evidence", response_model=CaseEvidenceCreateResponse, status_code=201)
def add_evidence_endpoint(
    case_id: int,
    payload: CaseEvidenceCreateRequest,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """Add a new evidence item to a case and link it via CollectedFor."""
    try:
        return add_case_evidence(db, case_id, payload, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/cases/{case_id}/evidence", response_model=CaseEvidenceListResponse)
def list_evidence_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """List all evidence items collected for a case."""
    try:
        return list_case_evidence(db, case_id, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/evidence/{evidence_id}", response_model=EvidenceRead)
def get_evidence_endpoint(evidence_id: int, db=Depends(get_db)):
    """Fetch a single evidence item by its ID."""
    try:
        return get_evidence(db, evidence_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/evidence/{evidence_id}", response_model=EvidenceRead)
def update_evidence_endpoint(
    evidence_id: int,
    description: str | None = None,
    location_id: int | None = None,
    collected_at: date | None = None,
    db=Depends(get_db),
):
    """Partially update an evidence record (description, location, collection date)."""
    try:
        return update_evidence(
            db,
            evidence_id,
            description=description,
            location_id=location_id,
            collected_at=collected_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
