"""
common.py
---------
Shared helpers used across all CRUD modules.

Utilities
---------
- build_full_name  : join first/middle/last name into one string
- not_found        : raise 404-equivalent ValueError
- require          : assert a condition or raise ValueError
- paginate         : apply offset/limit on a SQLAlchemy query
- build_person_summary : convert a Person ORM object → PersonSummary schema
- fetch_case      : fetch a CaseDetail by case_id, returning the latest open_date
- get_or_create_person : look-up or create a Person + role row inside a transaction
- assign_officer_to_case  : service – link a PoliceOfficer to a CaseDetail
- assign_judge_to_trial   : service – set judge_id on a Trial row
- link_suspect_evidence   : service – link a Suspect to an Evidence piece for a case
- unlink_officer_from_case: service – remove an officer assignment from a case
"""

from __future__ import annotations
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func
from App.db.models import *
from App.schema.core import *

# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def build_full_name(person: Person) -> str | None:
    """ Join first/middle/last name into one string """
    return (
        " ".join(
            part
            for part in [person.first_name, person.middle_name, person.last_name]
            if part
        )
        or None
    )

def not_found(entity: str, id_: object) -> None:
    """Raise ValueError for a missing record (HTTP 404 equivalent)."""
    raise ValueError(f"{entity} with id={id_!r} not found.")


def require(condition: bool, message: str) -> None:
    """Raise ValueError with *message* if *condition* is False."""
    if not condition:
        raise ValueError(message)


def paginate(query, page: int, page_size: int):
    """Apply OFFSET/LIMIT to a query. Returns (items, total_count)."""
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


# ---------------------------------------------------------------------------
# ORM → Schema helpers
# ---------------------------------------------------------------------------


def build_person_summary(person: Person) -> PersonSummary:
    """Convert a Person ORM row into a PersonSummary schema."""
    roles = [
        role
        for role, profile in [
            (PersonRole.OFFICER,  person.police_profile),
            (PersonRole.SUSPECT,  person.suspect_profile),
            (PersonRole.VICTIM,   person.victim_profile),
            (PersonRole.WITNESS,  person.witness_profile),
            (PersonRole.CRIMINAL, person.criminal_profile),
        ]
        if profile is not None
    ]

    return PersonSummary(
        person_id=person.person_id,
        first_name=person.first_name,
        middle_name=person.middle_name,
        last_name=person.last_name,
        full_name=build_full_name(person),
        address_id=person.address_id,
        roles=roles,
    )


# ---------------------------------------------------------------------------
# Case resolution
# ---------------------------------------------------------------------------

def fetch_case(db: Session, case_id: int, open_date: date | None = None) -> CaseDetail:
    """Fetch a CaseDetail by case_id (latest open_date if not specified). Raises ValueError if missing."""

    if open_date is not None: 
        case = (
            db.query(CaseDetail)
            .filter(CaseDetail.case_id == case_id, CaseDetail.open_date == open_date)
            .first()
        )
    else:
        case = (
            db.query(CaseDetail)
            .filter(CaseDetail.case_id == case_id)
            .order_by(CaseDetail.open_date.desc())
            .first()
        )

    if case is None:
        not_found("Case", case_id)

    return case  # type: ignore[return-value]


def fetch_trial(db: Session, case_id: int, trial_id: int) -> Trial:
    """Fetch a Trial by case_id + trial_number (latest open_date). Raises ValueError if missing."""
    trial = (
        db.query(Trial)
        .filter(Trial.case_id == case_id, Trial.trial_number == trial_id)
        .order_by(Trial.open_date.desc())
        .first()
    )
    if trial is None:
        not_found("Trial", trial_id)
    return trial  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Service: officer assignment
# ---------------------------------------------------------------------------

def assign_officer_to_case(
    db: Session,
    case_id: int,
    officer_person_id: int,
    open_date: date | None = None,
) -> AssignedTo:
    """Link a PoliceOfficer to a case. Creates AssignedTo row if absent. Does not commit."""
    case = fetch_case(db, case_id, open_date)

    officer = db.get(PoliceOfficer, officer_person_id)
    if officer is None:
        raise ValueError(
            f"Person {officer_person_id} is not registered as a police officer."
        )

    existing = (
        db.query(AssignedTo)
        .filter(
            AssignedTo.case_id == case.case_id,
            AssignedTo.open_date == case.open_date,
            AssignedTo.officer_person_id == officer_person_id,
        )
        .first()
    )
    if existing:
        return existing

    assignment = AssignedTo(
        officer_person_id=officer_person_id,
        case_id=case.case_id,
        open_date=case.open_date,
    )
    db.add(assignment)
    return assignment


def unlink_officer_from_case(
    db: Session,
    case_id: int,
    officer_person_id: int,
    open_date: date | None = None,
) -> bool:
    """Remove an officer–case assignment. Returns True if deleted, False if not found. Does not commit."""
    case = fetch_case(db, case_id, open_date)

    row = (
        db.query(AssignedTo)
        .filter(
            AssignedTo.case_id == case.case_id,
            AssignedTo.open_date == case.open_date,
            AssignedTo.officer_person_id == officer_person_id,
        )
        .first()
    )
    if row is None:
        return False
    
    db.delete(row)
    return True


# ---------------------------------------------------------------------------
# Service: judge assignment
# ---------------------------------------------------------------------------

def assign_judge_to_trial(
    db: Session,
    case_id: int,
    trial_id: int,
    judge_person_id: int,
) -> Trial:
    """Set judge_id on a Trial row. Validates the person exists. Does not commit."""
    trial = fetch_trial(db, case_id, trial_id)

    judge = db.get(Person, judge_person_id)
    if judge is None:
        not_found("Person (judge)", judge_person_id)

    trial.judge_id = judge_person_id  # type: ignore[assignment]
    return trial


# ---------------------------------------------------------------------------
# Service: link suspect ↔ evidence
# ---------------------------------------------------------------------------

def link_suspect_evidence(
    db: Session,
    case_id: int,
    suspect_person_id: int,
    evidence_id: int,
    open_date: date | None = None,
) -> LinkedTo:
    """Create a LinkedTo row for suspect ↔ evidence. Raises ValueError if evidence not on the case. Does not commit."""
    case = fetch_case(db, case_id, open_date)

    cf = (
        db.query(CollectedFor)
        .filter(
            CollectedFor.case_id == case.case_id,
            CollectedFor.open_date == case.open_date,
            CollectedFor.evidence_id == evidence_id,
        )
        .first()
    )
    if cf is None:
        raise ValueError(
            f"Evidence {evidence_id} is not collected for case {case_id}."
        )

    existing = (
        db.query(LinkedTo)
        .filter(
            LinkedTo.case_id == case.case_id,
            LinkedTo.open_date == case.open_date,
            LinkedTo.suspect_person_id == suspect_person_id,
            LinkedTo.evidence_id == evidence_id,
        )
        .first()
    )
    if existing:
        return existing

    link = LinkedTo(
        case_id=case.case_id,
        open_date=case.open_date,
        suspect_person_id=suspect_person_id,
        evidence_id=evidence_id,
    )
    db.add(link)
    return link


# ---------------------------------------------------------------------------
# Sequence helper (for tables without SERIAL / AUTOINCREMENT)
# ---------------------------------------------------------------------------

def next_id(db: Session, model, id_column: str) -> int:
    """Return MAX(id_column)+1 for the given model, or 1 if the table is empty."""
    col = getattr(model, id_column)
    result = db.query(func.max(col)).scalar()
    return (result or 0) + 1


def next_trial_number(db: Session, case_id: int, open_date: date) -> int:
    """Return the next trial_number for a given case."""
    result = (
        db.query(func.max(Trial.trial_number))
        .filter(Trial.case_id == case_id, Trial.open_date == open_date)
        .scalar()
    )
    return (result or 0) + 1
