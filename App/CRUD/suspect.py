"""
Functions for case suspect CRUD operations in the Crime Intelligence System.
- suspect_read: Converts a Suspect to a SuspectRead with person summary and linked evidence.
- add_case_suspect: Links a person to a case as a suspect and links any given evidence.
- list_case_suspects: Lists all suspects involved in a case.
- update_case_suspect: Updates the arrest status and details of a suspect.
- get_suspect: Fetches one suspect by person id.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session, joinedload, selectinload

from App.db.models import CaseDetail, InvolvedIn, Suspect
from App.schema.case import (
    CaseSuspectCreateRequest,
    CaseSuspectCreateResponse,
    CaseSuspectListResponse,
    CaseSuspectUpdateRequest,
    CaseSuspectUpdateResponse,
    SuspectRead,
    SuspectStatus,
)
from App.CRUD.common import (
    build_person_summary,
    fetch_case,
    get_or_create_link,
    link_suspect_evidence,
    not_found,
)
from App.CRUD.person import resolve_person


def suspect_read(suspect: Suspect) -> SuspectRead:
    return SuspectRead(
        suspect_id=suspect.suspect_person_id,
        person=build_person_summary(suspect.person) if suspect.person else None,
        physical_description=suspect.physical_description,
        family_contact=suspect.family_contact,
        arrest_status=(
            SuspectStatus(suspect.arrest_status) if suspect.arrest_status else None
        ),
        linked_evidence_ids=[lt.evidence_id for lt in suspect.linked_evidence],
    )


def _fetch_suspect(db: Session, suspect_id: int) -> Suspect:
    suspect = (
        db.query(Suspect)
        .options(selectinload(Suspect.linked_evidence), joinedload(Suspect.person))
        .filter(Suspect.suspect_person_id == suspect_id)
        .first()
    )
    if suspect is None:
        not_found("Suspect", suspect_id)
    return suspect


def add_case_suspect(
    db: Session,
    case_id: int,
    payload: CaseSuspectCreateRequest,
    open_date: date | None = None,
) -> CaseSuspectCreateResponse:
    case = fetch_case(db, case_id, open_date)
    person_id = resolve_person(db, payload)

    suspect = db.get(Suspect, person_id)
    if suspect is None:
        suspect = Suspect(suspect_person_id=person_id)
        db.add(suspect)
        db.flush()

    get_or_create_link(
        db,
        InvolvedIn,
        case_id=case.case_id,
        open_date=case.open_date,
        suspect_person_id=person_id,
    )

    bad_ids = []
    for evidence_id in payload.evidence_ids:
        try:
            link_suspect_evidence(db, case, person_id, evidence_id)
        except ValueError:
            bad_ids.append(evidence_id)
    if bad_ids:
        raise ValueError(f"Evidence IDs not collected for case {case_id}: {bad_ids}")

    db.flush()
    db.refresh(suspect)

    return CaseSuspectCreateResponse(
        suspect_id=person_id, suspect=suspect_read(suspect)
    )


def list_case_suspects(
    db: Session,
    case_id: int,
    open_date: date | None = None,
) -> CaseSuspectListResponse:
    case = fetch_case(
        db,
        case_id,
        open_date,
        selectinload(CaseDetail.involved_in_entries)
        .joinedload(InvolvedIn.suspect)
        .selectinload(Suspect.linked_evidence),
    )

    return CaseSuspectListResponse(
        case_id=case.case_id,
        open_date=case.open_date,
        items=[
            suspect_read(entry.suspect)
            for entry in case.involved_in_entries
            if entry.suspect
        ],
    )


def update_case_suspect(
    db: Session,
    case_id: int,
    suspect_id: int,
    payload: CaseSuspectUpdateRequest,
    open_date: date | None = None,
) -> CaseSuspectUpdateResponse:
    case = fetch_case(db, case_id, open_date)

    linked = (
        db.query(InvolvedIn)
        .filter(
            InvolvedIn.case_id == case.case_id,
            InvolvedIn.open_date == case.open_date,
            InvolvedIn.suspect_person_id == suspect_id,
        )
        .first()
    )
    if linked is None:
        raise ValueError(f"Suspect {suspect_id} is not linked to case {case_id}.")

    suspect = db.get(Suspect, suspect_id)
    if suspect is None:
        raise ValueError(f"Person {suspect_id} is not registered as a suspect.")

    given = payload.model_dump(exclude_unset=True)

    if payload.arrest_status is not None:
        suspect.arrest_status = payload.arrest_status.value
    if "physical_description" in given:
        suspect.physical_description = payload.physical_description
    if "family_contact" in given:
        suspect.family_contact = payload.family_contact

    db.flush()
    db.refresh(suspect)

    return CaseSuspectUpdateResponse(
        suspect_id=suspect_id, suspect=suspect_read(suspect)
    )


def get_suspect(db: Session, suspect_id: int) -> SuspectRead:
    return suspect_read(_fetch_suspect(db, suspect_id))
