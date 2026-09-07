from datetime import date

from fastapi import APIRouter, Depends, Query

from App.API.deps import get_db
from App.schema.case import (
    CaseTrialListResponse,
    TrialCreateRequest,
    TrialCreateResponse,
    TrialDetailResponse,
    TrialHearingCreateRequest,
    TrialHearingCreateResponse,
    TrialPunishmentCreateRequest,
    TrialPunishmentCreateResponse,
)
from App.schema.core import MessageResponse
from App.CRUD.trial import (
    add_case_trial,
    add_trial_hearing,
    apply_trial_punishment,
    get_trial_detail,
    list_case_trials,
)
from App.CRUD.common import assign_judge_to_trial

router = APIRouter(tags=["trials"])


@router.post("/cases/{case_id}/trials", response_model=TrialCreateResponse, status_code=201)
def add_trial_endpoint(
    case_id: int,
    payload: TrialCreateRequest,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    return add_case_trial(db, case_id, payload, open_date)


@router.get("/cases/{case_id}/trials", response_model=CaseTrialListResponse)
def list_trials_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    return list_case_trials(db, case_id, open_date)


@router.get("/cases/{case_id}/trials/{trial_id}", response_model=TrialDetailResponse)
def get_trial_endpoint(
    case_id: int,
    trial_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    return get_trial_detail(db, case_id, trial_id, open_date)


@router.post(
    "/cases/{case_id}/trials/{trial_id}/hearing",
    response_model=TrialHearingCreateResponse,
    status_code=201,
)
def add_hearing_endpoint(
    case_id: int,
    trial_id: int,
    payload: TrialHearingCreateRequest,
    db=Depends(get_db),
):
    return add_trial_hearing(db, case_id, trial_id, payload)


@router.post(
    "/cases/{case_id}/trials/{trial_id}/punishment",
    response_model=TrialPunishmentCreateResponse,
    status_code=201,
)
def apply_punishment_endpoint(
    case_id: int,
    trial_id: int,
    payload: TrialPunishmentCreateRequest,
    db=Depends(get_db),
):
    return apply_trial_punishment(db, case_id, trial_id, payload)


@router.post(
    "/cases/{case_id}/trials/{trial_id}/judge/{judge_id}",
    response_model=MessageResponse,
)
def assign_judge_endpoint(
    case_id: int,
    trial_id: int,
    judge_id: int,
    db=Depends(get_db),
):
    assign_judge_to_trial(db, case_id, trial_id, judge_id)
    return MessageResponse(
        detail=f"Judge {judge_id} assigned to trial {trial_id} of case {case_id}."
    )
