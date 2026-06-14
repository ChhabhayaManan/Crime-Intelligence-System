"""
witnesses.py
------------
FastAPI router for Witness and Testimony endpoints.

Endpoints
---------
  POST   /cases/{case_id}/witnesses                            – add_case_witness
  GET    /cases/{case_id}/witnesses                            – list_case_witnesses
  POST   /cases/{case_id}/witnesses/{witness_id}/testimony     – record_testimony
  GET    /cases/{case_id}/testimonies                          – list_case_testimonies
"""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from App.API.deps import get_db
from App.schema.case import (
    CaseWitnessCreateRequest,
    CaseWitnessCreateResponse,
    CaseWitnessListResponse,
    TestimonyRead,
    WitnessTestimonyCreateRequest,
)
from App.CRUD.witness import (
    add_case_witness,
    record_testimony,
    list_case_testimonies,
    list_case_witnesses,
)
router = APIRouter(tags=["witnesses"])


@router.post("/cases/{case_id}/witnesses", response_model=CaseWitnessCreateResponse, status_code=201)
def add_witness_endpoint(
    case_id: int,
    payload: CaseWitnessCreateRequest,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """Add a witness to a case (by existing person_id or inline new person)."""
    try:
        return add_case_witness(db, case_id, payload, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/cases/{case_id}/witnesses", response_model=CaseWitnessListResponse)
def list_witnesses_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """List all witnesses linked to a case."""
    try:
        return list_case_witnesses(db, case_id, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/cases/{case_id}/witnesses/{witness_id}/testimony",
    response_model=TestimonyRead,
    status_code=201,
)
def add_testimony_endpoint(
    case_id: int,
    witness_id: int,
    payload: WitnessTestimonyCreateRequest,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """Record or update a witness's testimony and the suspects they point to."""
    try:
        return record_testimony(db, case_id, witness_id, payload, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/cases/{case_id}/testimonies", response_model=List[TestimonyRead])
def list_testimonies_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """List all testimony records for a case."""
    try:
        return list_case_testimonies(db, case_id, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
