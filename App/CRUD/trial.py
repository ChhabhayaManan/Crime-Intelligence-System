"""
Functions for trial and punishment CRUD operations in the Crime Intelligence System.
- trial_read: Converts a Trial to a TrialRead.
- _derive_punishment_type: Derives a punishment type label from a Punishment row.
- _punishment_read: Converts a Punishment to a PunishmentRead.
- add_case_trial: Creates a new trial for a case.
- list_case_trials: Lists all trials of a case.
- add_trial_hearing: Records a hearing, opening a new trial row if one is already set.
- get_trial_detail: Fetches a trial with its punishments.
- apply_trial_punishment: Creates or updates punishments for the given persons on a trial.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session, selectinload

from App.db.models import CaseDetail, Criminal, Punishment, Trial
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
from App.CRUD.common import fetch_case, fetch_trial, next_trial_number


def trial_read(trial: Trial) -> TrialRead:
    return TrialRead(
        case_id=trial.case_id,
        open_date=trial.open_date,
        trial_number=trial.trial_number,
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


def add_case_trial(
    db: Session,
    case_id: int,
    payload: TrialCreateRequest,
    open_date: date | None = None,
) -> TrialCreateResponse:
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
    db.flush()

    return TrialCreateResponse(trial_id=trial_num, trial=trial_read(trial))


def list_case_trials(
    db: Session,
    case_id: int,
    open_date: date | None = None,
) -> CaseTrialListResponse:
    case = fetch_case(db, case_id, open_date, selectinload(CaseDetail.trials))

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
    existing = fetch_trial(db, case_id, trial_id)

    if existing.hearing is not None:
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

    db.flush()

    return TrialHearingCreateResponse(trial_id=trial_num, trial=trial_read(trial))


def get_trial_detail(
    db: Session,
    case_id: int,
    trial_id: int,
) -> TrialDetailResponse:
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
    trial = fetch_trial(db, case_id, trial_id)

    given = payload.model_dump(exclude_unset=True)
    punishments: list[PunishmentRead] = []

    for person_id in payload.person_ids:
        if db.get(Criminal, person_id) is None:
            db.add(Criminal(criminal_person_id=person_id))
            db.flush()

        punishment = (
            db.query(Punishment)
            .filter(
                Punishment.criminal_person_id == person_id,
                Punishment.case_id == trial.case_id,
                Punishment.open_date == trial.open_date,
            )
            .first()
        )
        if punishment is None:
            punishment = Punishment(
                criminal_person_id=person_id,
                case_id=trial.case_id,
                open_date=trial.open_date,
            )
            db.add(punishment)

        if "fine" in given:
            punishment.fine = payload.fine
        if "jail_start" in given:
            punishment.jail_start_date = payload.jail_start
        if "jail_end" in given:
            punishment.jail_end_date = payload.jail_end
        if "death_penalty" in given:
            punishment.death_penalty = payload.death_penalty

        db.flush()
        punishments.append(_punishment_read(punishment))

    return TrialPunishmentCreateResponse(
        trial_id=trial_id,
        punishments=punishments,
    )
