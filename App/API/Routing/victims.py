from datetime import date

from fastapi import APIRouter, Depends, Query

from App.API.deps import get_db
from App.schema.case import (
    CaseVictimCreateRequest,
    CaseVictimCreateResponse,
    CaseVictimListResponse,
    VictimListResponse,
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
    return add_case_victim(db, case_id, payload, open_date)


@router.get("/cases/{case_id}/victims", response_model=CaseVictimListResponse)
def list_case_victims_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    return list_case_victims(db, case_id, open_date)


@router.get("/victims", response_model=VictimListResponse)
def list_victims_endpoint(
    query: str | None = Query(default=None, description="Free-text name search"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db=Depends(get_db),
):
    return list_victims(db, query=query, page=page, page_size=page_size)
