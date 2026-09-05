from datetime import date

from fastapi import APIRouter, Depends, Query

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
    return add_case_suspect(db, case_id, payload, open_date)


@router.get("/cases/{case_id}/suspects", response_model=CaseSuspectListResponse)
def list_suspects_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    return list_case_suspects(db, case_id, open_date)


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
    return update_case_suspect(db, case_id, suspect_id, payload, open_date)


@router.get("/suspects/{suspect_id}", response_model=SuspectRead)
def get_suspect_endpoint(suspect_id: int, db=Depends(get_db)):
    return get_suspect(db, suspect_id)
