"""
trial.py
--------
CRUD operations for Trials, Hearings, and Punishments.

Functions
---------
  add_case_trial        – POST /cases/{case_id}/trials
  list_case_trials      – GET  /cases/{case_id}/trials
  add_trial_hearing     – POST /trials/{trial_id}/hearing
  get_trial_detail      – GET  /trials/{trial_id}
  apply_trial_punishment– POST /trials/{trial_id}/punishment
  assign_judge_to_trial [service] – set judge on a trial (no direct HTTP route)
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from App.db.models import (
    Criminal,
    Punishment,
    Trial,
)
from App.schema.case import (
    CaseTrialListResponse,
    PunishmentRead,
    TrialCreateRequest,
    TrialCreateResponse,
    TrialDetailResponse,
    TrialHearingCreateRequest,
    TrialHearingCreateResponse,
    TrialPunishmentCreateRequest,
    TrialPunishmentCreateResponse,
    TrialRead,
)
from App.CRUD.common import (
    next_trial_number,
    fetch_case,
    fetch_trial,
)

# ---------------------------------------------------------------------------
# Internal mapper
# ---------------------------------------------------------------------------

def trial_read(trial: Trial) -> TrialRead:
    return TrialRead(
        case_id=trial.case_id,
        open_date=trial.open_date,
        trial_number=trial.trial_number,
        trial_id=trial.trial_number,
        hearing_date=trial.hearing,
        judge_id=trial.judge_id,
        court_level=trial.court_level,
    )


def _derive_punishment_type(p: Punishment) -> str | None:
    if p.death_penalty == "Y":
        return "death_penalty"
    if p.jail_start_date is not None or p.jail_end_date is not None:
        return "jail"
    if p.fine is not None:
        return "fine"
    return None


def _punishment_read(p: Punishment) -> PunishmentRead:
    return PunishmentRead(
        criminal_person_id=p.criminal_person_id,
        case_id=p.case_id,
        open_date=p.open_date,
        fine=p.fine,
        jail_start_date=p.jail_start_date,
        jail_end_date=p.jail_end_date,
        death_penalty=p.death_penalty,
        punishment_type=_derive_punishment_type(p),
    )


# ---------------------------------------------------------------------------
# Public CRUD
# ---------------------------------------------------------------------------

def add_case_trial(
    db: Session,
    case_id: int,
    payload: TrialCreateRequest,
    open_date: date | None = None,
) -> TrialCreateResponse:
    """Create a new trial for a case."""
    case = fetch_case(db, case_id, open_date)

    trial_num = next_trial_number(db, case.case_id, case.open_date)
    trial = Trial(
        case_id=case.case_id,
        open_date=case.open_date,
        trial_number=trial_num,
        hearing=payload.hearing_date,
        judge_id=payload.judge_id,
        court_level=payload.court_level,
    )
    db.add(trial)
    db.commit()
    db.refresh(trial)

    return TrialCreateResponse(trial_id=trial_num, trial=trial_read(trial))


def list_case_trials(
    db: Session,
    case_id: int,
    open_date: date | None = None,
) -> CaseTrialListResponse:
    """Return all trials for a case."""
    case = fetch_case(db, case_id, open_date)

    return CaseTrialListResponse(
        case_id=case.case_id,
        items=[trial_read(t) for t in case.trials],
    )


def add_trial_hearing(
    db: Session,
    case_id: int,
    trial_id: int,
    payload: TrialHearingCreateRequest,
) -> TrialHearingCreateResponse:
    """Record a hearing on a trial. If the trial already has a hearing date set, creates a new trial row for this hearing."""
    existing = fetch_trial(db, case_id, trial_id)

    if existing.hearing is not None:
        # Trial already has a hearing — create next trial for this hearing
        trial_num = next_trial_number(db, existing.case_id, existing.open_date)
        trial = Trial(
            case_id=existing.case_id,
            open_date=existing.open_date,
            trial_number=trial_num,
            judge_id=existing.judge_id,
            court_level=existing.court_level,
        )
        db.add(trial)
        db.flush()
    else:
        trial = existing
        trial_num = existing.trial_number

    if payload.hearing_date is not None:
        trial.hearing = payload.hearing_date

    if payload.outcome is not None:
        trial.court_level = payload.outcome[:50]

    db.commit()
    db.refresh(trial)

    return TrialHearingCreateResponse(trial_id=trial_num, trial=trial_read(trial))


def get_trial_detail(
    db: Session,
    case_id: int,
    trial_id: int,
) -> TrialDetailResponse:
    """Fetch a trial along with all its punishment records."""
    trial = fetch_trial(db, case_id, trial_id)

    punishments = (
        db.query(Punishment)
        .filter(
            Punishment.case_id == trial.case_id,
            Punishment.open_date == trial.open_date,
        )
        .all()
    )

    return TrialDetailResponse(
        trial=trial_read(trial),
        punishments=[_punishment_read(p) for p in punishments],
    )


def apply_trial_punishment(
    db: Session,
    case_id: int,
    trial_id: int,
    payload: TrialPunishmentCreateRequest,
) -> TrialPunishmentCreateResponse:
    """Assign punishment to one or more criminals. Creates Criminal profile and upserts Punishment row per person."""
    trial = fetch_trial(db, case_id, trial_id)

    punishments_created: list[PunishmentRead] = []

    for person_id in payload.person_ids:
        # Ensure Criminal profile
        criminal = db.get(Criminal, person_id)
        if criminal is None:
            criminal = Criminal(criminal_person_id=person_id)
            db.add(criminal)
            db.flush()

        # Upsert Punishment
        p = (
            db.query(Punishment)
            .filter(
                Punishment.criminal_person_id == person_id,
                Punishment.case_id == trial.case_id,
                Punishment.open_date == trial.open_date,
            )
            .first()
        )
        if p is None:
            p = Punishment(
                criminal_person_id=person_id,
                case_id=trial.case_id,
                open_date=trial.open_date,
            )
            db.add(p)

        p.fine = payload.fine
        p.jail_start_date = payload.jail_start
        p.jail_end_date = payload.jail_end
        p.death_penalty = payload.death_penalty

        db.flush()
        punishments_created.append(_punishment_read(p))

    db.commit()

    return TrialPunishmentCreateResponse(
        trial_id=trial_id,
        punishments=punishments_created,
    )
