"""
Functions for case victim CRUD operations in the Crime Intelligence System.
- victim_read: Converts a Victim to a VictimRead with person summary.
- add_case_victim: Links a person to a case as a victim.
- list_case_victims: Lists all victims affected by a case.
- list_victims: Lists victims across all cases by name search, paginated.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from App.db.models import AffectedBy, CaseDetail, Person, Victim
from App.schema.case import (
    CaseVictimCreateRequest,
    CaseVictimCreateResponse,
    CaseVictimListResponse,
    VictimListResponse,
    VictimRead,
)
from App.schema.core import PageMeta
from App.CRUD.common import (
    build_person_summary,
    fetch_case,
    get_or_create_link,
    paginate,
)
from App.CRUD.person import resolve_person


def victim_read(victim: Victim) -> VictimRead:
    return VictimRead(
        victim_id=victim.victim_person_id,
        person=build_person_summary(victim.person) if victim.person else None,
        harm_details=victim.harm_details,
        family_contact=victim.family_contact,
    )


def add_case_victim(
    db: Session,
    case_id: int,
    payload: CaseVictimCreateRequest,
    open_date: date | None = None,
) -> CaseVictimCreateResponse:
    case = fetch_case(db, case_id, open_date)
    person_id = resolve_person(db, payload)

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

    get_or_create_link(
        db,
        AffectedBy,
        case_id=case.case_id,
        open_date=case.open_date,
        victim_person_id=person_id,
    )
    db.flush()

    return CaseVictimCreateResponse(victim_id=person_id, victim=victim_read(victim))


def list_case_victims(
    db: Session,
    case_id: int,
    open_date: date | None = None,
) -> CaseVictimListResponse:
    case = fetch_case(
        db,
        case_id,
        open_date,
        selectinload(CaseDetail.affected_by_entries).joinedload(AffectedBy.victim),
    )

    return CaseVictimListResponse(
        case_id=case.case_id,
        open_date=case.open_date,
        items=[
            victim_read(entry.victim)
            for entry in case.affected_by_entries
            if entry.victim
        ],
    )


def list_victims(
    db: Session,
    query: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> VictimListResponse:
    q = (
        db.query(Victim)
        .join(Person, Person.person_id == Victim.victim_person_id)
        .options(joinedload(Victim.person))
    )

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
        items=[victim_read(v) for v in items],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )
