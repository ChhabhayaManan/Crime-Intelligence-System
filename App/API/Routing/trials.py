"""
trials.py
---------
FastAPI router for Trial, Hearing, and Punishment endpoints.

Endpoints
---------
  POST   /cases/{case_id}/trials                          – add_case_trial
  GET    /cases/{case_id}/trials                          – list_case_trials
  GET    /cases/{case_id}/trials/{trial_id}               – get_trial_detail
  POST   /cases/{case_id}/trials/{trial_id}/hearing       – add_trial_hearing
  POST   /cases/{case_id}/trials/{trial_id}/punishment    – apply_trial_punishment
  POST   /cases/{case_id}/trials/{trial_id}/judge/{judge_id} – assign_judge_to_trial
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

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
    """Create a new trial for a case, with optional judge and hearing date."""
    try:
        return add_case_trial(db, case_id, payload, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/cases/{case_id}/trials", response_model=CaseTrialListResponse)
def list_trials_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """List all trials associated with a case."""
    try:
        return list_case_trials(db, case_id, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/cases/{case_id}/trials/{trial_id}", response_model=TrialDetailResponse)
def get_trial_endpoint(
    case_id: int,
    trial_id: int,
    db=Depends(get_db),
):
    """Fetch a trial's full details including all punishment records."""
    try:
        return get_trial_detail(db, case_id, trial_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


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
    """Record a hearing outcome and notes for a trial."""
    try:
        return add_trial_hearing(db, case_id, trial_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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
    """Assign punishment (fine, jail, death penalty) to one or more criminals linked to this trial."""
    try:
        return apply_trial_punishment(db, case_id, trial_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/cases/{case_id}/trials/{trial_id}/judge/{judge_id}", status_code=200)
def assign_judge_endpoint(
    case_id: int,
    trial_id: int,
    judge_id: int,
    db=Depends(get_db),
):
    """Assign a judge (by person_id) to a specific trial."""
    try:
        assign_judge_to_trial(db, case_id, trial_id, judge_id)
        db.commit()
        return {"detail": f"Judge {judge_id} assigned to trial {trial_id} of case {case_id}."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
