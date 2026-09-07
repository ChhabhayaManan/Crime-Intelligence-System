from datetime import date

from fastapi import APIRouter, Depends, Query

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
from App.schema.core import MessageResponse
from App.CRUD.case import (
    close_case,
    get_case,
    get_case_details,
    list_cases,
    open_case,
    update_case,
)
from App.CRUD.common import assign_officer_to_case, not_found, unlink_officer_from_case

router = APIRouter(tags=["cases"])


@router.post("/cases", response_model=CaseOpenResponse, status_code=201)
def open_case_endpoint(payload: CaseOpenRequest, db=Depends(get_db)):
    return open_case(db, payload)


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


@router.get("/cases/{case_id}", response_model=CaseRead)
def get_case_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    return get_case(db, case_id, open_date)


@router.patch("/cases/{case_id}", response_model=CaseRead)
def update_case_endpoint(
    case_id: int,
    payload: CaseUpdateRequest,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    return update_case(db, case_id, payload, open_date)


@router.patch("/cases/{case_id}/close", response_model=CaseCloseResponse)
def close_case_endpoint(
    case_id: int,
    payload: CaseCloseRequest,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    return close_case(db, case_id, payload, open_date)


@router.get("/cases/{case_id}/details", response_model=CaseDetailResponse)
def get_case_details_endpoint(
    case_id: int,
    include: list[CaseInclude] | None = Query(default=None),
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    return get_case_details(db, case_id, include, open_date)


@router.post("/cases/{case_id}/officers/{officer_id}", response_model=MessageResponse)
def assign_officer_endpoint(
    case_id: int,
    officer_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    assign_officer_to_case(db, case_id, officer_id, open_date)
    return MessageResponse(detail=f"Officer {officer_id} assigned to case {case_id}.")


@router.delete("/cases/{case_id}/officers/{officer_id}", response_model=MessageResponse)
def unlink_officer_endpoint(
    case_id: int,
    officer_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    if not unlink_officer_from_case(db, case_id, officer_id, open_date):
        not_found("Officer assignment", officer_id)
    return MessageResponse(detail=f"Officer {officer_id} unlinked from case {case_id}.")
