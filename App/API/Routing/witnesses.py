from datetime import date

from fastapi import APIRouter, Depends, Query

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
    return add_case_witness(db, case_id, payload, open_date)


@router.get("/cases/{case_id}/witnesses", response_model=CaseWitnessListResponse)
def list_witnesses_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    return list_case_witnesses(db, case_id, open_date)


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
    return record_testimony(db, case_id, witness_id, payload, open_date)


@router.get("/cases/{case_id}/testimonies", response_model=list[TestimonyRead])
def list_testimonies_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    return list_case_testimonies(db, case_id, open_date)
