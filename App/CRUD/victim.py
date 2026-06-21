"""
victim.py
---------
CRUD operations for Victims.

Functions
---------
  add_case_victim    – POST /cases/{case_id}/victims
  list_case_victims  – GET  /cases/{case_id}/victims
  list_victims       – GET  /victims (global list)
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session

from App.db.models import (
    AffectedBy,
    Person,
    Victim,
)
from App.schema.case import (
    CaseVictimCreateRequest,
    CaseVictimCreateResponse,
    CaseVictimListResponse,
    VictimListResponse,
    VictimRead,
)
from App.schema.core import PageMeta
from App.CRUD.common import build_person_summary, not_found, paginate, fetch_case

# ---------------------------------------------------------------------------
# Internal mapper
# ---------------------------------------------------------------------------

def _victim_read(victim: Victim) -> VictimRead:
    person = build_person_summary(victim.person) if victim.person else None
    return VictimRead(
        victim_id=victim.victim_person_id,
        person=person,
        harm_details=victim.harm_details,
        family_contact=victim.family_contact,
    )


# ---------------------------------------------------------------------------
# Public CRUD
# ---------------------------------------------------------------------------

def add_case_victim(
    db: Session,
    case_id: int,
    payload: CaseVictimCreateRequest,
    open_date: date | None = None,
) -> CaseVictimCreateResponse:
    """Add a victim to a case (by existing person_id or inline PersonCreate). Creates Victim profile and AffectedBy link."""
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

    # Ensure Victim profile
    victim = db.get(Victim, person_id)
    if victim is None:
        victim = Victim(
            victim_person_id=person_id,
            harm_details=payload.harm_details,
            family_contact=payload.family_contact,
        )
        db.add(victim)
        db.flush()
    else:
        if payload.harm_details:
            victim.harm_details = payload.harm_details
        if payload.family_contact:
            victim.family_contact = payload.family_contact

    # Ensure AffectedBy link
    ab = (
        db.query(AffectedBy)
        .filter(
            AffectedBy.case_id == case.case_id,
            AffectedBy.open_date == case.open_date,
            AffectedBy.victim_person_id == person_id,
        )
        .first()
    )
    if ab is None:
        ab = AffectedBy(
            case_id=case.case_id,
            open_date=case.open_date,
            victim_person_id=person_id,
        )
        db.add(ab)

    db.commit()
    db.refresh(victim)

    vr = _victim_read(victim)
    return CaseVictimCreateResponse(victim_id=person_id, victim=vr)


def list_case_victims(
    db: Session,
    case_id: int,
    open_date: date | None = None,
) -> CaseVictimListResponse:
    """Return all victims affected by a given case."""
    case = fetch_case(db, case_id, open_date)

    victims = [
        _victim_read(ab.victim)
        for ab in case.affected_by_entries
        if ab.victim
    ]
    return CaseVictimListResponse(
        case_id=case.case_id,
        open_date=case.open_date,
        items=victims,
    )


def list_victims(
    db: Session,
    query: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> VictimListResponse:
    """Global victim list with optional name filter."""
    q = db.query(Victim).join(Person, Person.person_id == Victim.victim_person_id)

    if query:
        like = f"%{query}%"
        q = q.filter(
            or_(
                Person.first_name.ilike(like),
                Person.last_name.ilike(like),
                Person.middle_name.ilike(like),
            )
        )

    items, total = paginate(q, page, page_size)
    return VictimListResponse(
        items=[_victim_read(v) for v in items],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )
