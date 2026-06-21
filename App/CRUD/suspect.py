"""
suspect.py
----------
CRUD operations for Suspects.

Functions
---------
  add_case_suspect     – POST /cases/{case_id}/suspects
  list_case_suspects   – GET  /cases/{case_id}/suspects
  update_case_suspect  – PATCH /cases/{case_id}/suspects/{suspect_id}
  get_suspect          – GET  /suspects/{suspect_id}
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from App.db.models import (
    InvolvedIn,
    LinkedTo,
    Person,
    Suspect,
)
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
    link_suspect_evidence,
    not_found,
    fetch_case,
)

# ---------------------------------------------------------------------------
# Internal mapper
# ---------------------------------------------------------------------------

def _suspect_read(suspect: Suspect) -> SuspectRead:
    person = build_person_summary(suspect.person) if suspect.person else None
    linked = [lt.evidence_id for lt in suspect.linked_evidence]
    return SuspectRead(
        suspect_id=suspect.suspect_person_id,
        person=person,
        physical_description=suspect.physical_description,
        family_contact=suspect.family_contact,
        arrest_status=(
            SuspectStatus(suspect.arrest_status) if suspect.arrest_status else None
        ),
        linked_evidence_ids=linked,
    )


# ---------------------------------------------------------------------------
# Public CRUD
# ---------------------------------------------------------------------------

def add_case_suspect(
    db: Session,
    case_id: int,
    payload: CaseSuspectCreateRequest,
    open_date: date | None = None,
) -> CaseSuspectCreateResponse:
    """Add a suspect to a case (by existing person_id or inline PersonCreate). Creates profile and InvolvedIn link."""
    case = fetch_case(db, case_id, open_date)

    # Resolve person
    if payload.person_id is not None:
        person = db.get(Person, payload.person_id)
        if person is None:
            not_found("Person", payload.person_id)
    else:
        from App.CRUD.person import create_person
        result = create_person(db, payload.person)  # type: ignore[arg-type]
        person = db.get(Person, result.person_id)

    person_id: int = person.person_id  # type: ignore[union-attr]

    # Ensure Suspect profile exists
    suspect = db.get(Suspect, person_id)
    if suspect is None:
        suspect = Suspect(suspect_person_id=person_id)
        db.add(suspect)
        db.flush()

    # Ensure InvolvedIn link
    inv = (
        db.query(InvolvedIn)
        .filter(
            InvolvedIn.case_id == case.case_id,
            InvolvedIn.open_date == case.open_date,
            InvolvedIn.suspect_person_id == person_id,
        )
        .first()
    )
    if inv is None:
        inv = InvolvedIn(
            case_id=case.case_id,
            open_date=case.open_date,
            suspect_person_id=person_id,
        )
        db.add(inv)
        db.flush()

    # Link evidence — fail fast on invalid IDs
    bad_ids = []
    for ev_id in payload.evidence_ids:
        try:
            link_suspect_evidence(db, case.case_id, person_id, ev_id, case.open_date)
        except ValueError:
            bad_ids.append(ev_id)
    if bad_ids:
        raise ValueError(f"Evidence IDs not collected for case {case_id}: {bad_ids}")

    db.commit()
    db.refresh(suspect)

    sr = _suspect_read(suspect)
    return CaseSuspectCreateResponse(suspect_id=person_id, suspect=sr)


def list_case_suspects(
    db: Session,
    case_id: int,
    open_date: date | None = None,
) -> CaseSuspectListResponse:
    """Return all suspects linked to a case."""
    case = fetch_case(db, case_id, open_date)

    suspects = [
        _suspect_read(inv.suspect)
        for inv in case.involved_in_entries
        if inv.suspect
    ]
    return CaseSuspectListResponse(
        case_id=case.case_id,
        open_date=case.open_date,
        items=suspects,
    )


def update_case_suspect(
    db: Session,
    case_id: int,
    suspect_id: int,
    payload: CaseSuspectUpdateRequest,
    open_date: date | None = None,
) -> CaseSuspectUpdateResponse:
    """Update suspect arrest status, physical description, bail info."""
    case = fetch_case(db, case_id, open_date)

    inv = (
        db.query(InvolvedIn)
        .filter(
            InvolvedIn.case_id == case.case_id,
            InvolvedIn.open_date == case.open_date,
            InvolvedIn.suspect_person_id == suspect_id,
        )
        .first()
    )
    if inv is None:
        raise ValueError(f"Suspect {suspect_id} is not linked to case {case_id}.")

    suspect = db.get(Suspect, suspect_id)
    if suspect is None:
        raise ValueError(f"Person {suspect_id} is not registered as a suspect.")

    if payload.arrest_status is not None:
        suspect.arrest_status = payload.arrest_status.value
    if payload.physical_description is not None:
        suspect.physical_description = payload.physical_description
    if payload.family_contact is not None:
        suspect.family_contact = payload.family_contact

    db.commit()
    db.refresh(suspect)

    sr = _suspect_read(suspect)
    return CaseSuspectUpdateResponse(suspect_id=suspect_id, suspect=sr)


def get_suspect(db: Session, suspect_id: int) -> SuspectRead:
    """Fetch a single suspect by person_id."""
    suspect = db.get(Suspect, suspect_id)
    if suspect is None:
        not_found("Suspect", suspect_id)
    return _suspect_read(suspect)  # type: ignore[arg-type]
