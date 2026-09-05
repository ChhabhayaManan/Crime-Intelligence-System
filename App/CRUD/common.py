"""
Functions for common CRUD operations and utilities in the Crime Intelligence System.
- build_full_name: Constructs a full name from a Person object.
- NotFoundError: ValueError subclass the API maps to 404.
- not_found: Raises a NotFoundError when an entity is not found.
- paginate: Paginates a SQLAlchemy query.
- person_roles: Lists the roles a Person currently holds.
- build_person_summary: Builds a summary of a Person, including their roles.
- get_or_create_link: Fetches a junction row by its keys, creating it when absent.
- fetch_case: Fetches a CaseDetail by case_id and optional open_date.
- fetch_trial: Fetches a Trial by case_id and trial_id.
- assign_officer_to_case: Assigns a police officer to a case.
- unlink_officer_from_case: Unlinks a police officer from a case.
- assign_judge_to_trial: Assigns a judge to a trial.
- link_suspect_evidence: Links a suspect to evidence already collected for a case.
- next_trial_number: Returns the next trial number, locking the case row to serialise concurrent callers.
"""
from __future__ import annotations

from datetime import date
from typing import NoReturn

from sqlalchemy import func
from sqlalchemy.orm import Session

from App.db.models import (
    AssignedTo,
    CaseDetail,
    CollectedFor,
    LinkedTo,
    Person,
    PoliceOfficer,
    Trial,
)
from App.schema.core import PersonRole, PersonSummary

PERSON_ROLE_ATTRS = (
    (PersonRole.OFFICER, "police_profile"),
    (PersonRole.SUSPECT, "suspect_profile"),
    (PersonRole.VICTIM, "victim_profile"),
    (PersonRole.WITNESS, "witness_profile"),
    (PersonRole.CRIMINAL, "criminal_profile"),
)


def build_full_name(person: Person) -> str | None:
    return (
        " ".join(
            part
            for part in [person.first_name, person.middle_name, person.last_name]
            if part
        )
        or None
    )


class NotFoundError(ValueError):
    pass


def not_found(entity: str, id_: object) -> NoReturn:
    raise NotFoundError(f"{entity} with id={id_!r} not found.")


def paginate(query, page: int, page_size: int):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def person_roles(person: Person) -> list[PersonRole]:
    return [role for role, attr in PERSON_ROLE_ATTRS if getattr(person, attr) is not None]



def build_person_summary(person: Person) -> PersonSummary:
    return PersonSummary(
        person_id=person.person_id,
        first_name=person.first_name,
        middle_name=person.middle_name,
        last_name=person.last_name,
        full_name=build_full_name(person),
        address_id=person.address_id,
        roles=person_roles(person),
    )


def get_or_create_link(db: Session, model, **keys):
    row = db.query(model).filter_by(**keys).first()
    if row is None:
        row = model(**keys)
        db.add(row)
        db.flush()
    return row


def fetch_case(
    db: Session,
    case_id: int,
    open_date: date | None = None,
    *load,
) -> CaseDetail:
    q = db.query(CaseDetail).options(*load).filter(CaseDetail.case_id == case_id)
    if open_date is not None:
        q = q.filter(CaseDetail.open_date == open_date)
    else:
        q = q.order_by(CaseDetail.open_date.desc())

    case = q.first()
    if case is None:
        not_found("Case", case_id)
    return case


def fetch_trial(
    db: Session,
    case_id: int,
    trial_id: int,
    open_date: date | None = None,
) -> Trial:
    q = db.query(Trial).filter(
        Trial.case_id == case_id, Trial.trial_number == trial_id
    )
    if open_date is not None:
        q = q.filter(Trial.open_date == open_date)

    trial = q.order_by(Trial.open_date.desc()).first()
    if trial is None:
        not_found("Trial", trial_id)
    return trial


def assign_officer_to_case(
    db: Session,
    case_id: int,
    officer_person_id: int,
    open_date: date | None = None,
) -> AssignedTo:
    case = fetch_case(db, case_id, open_date)

    if db.get(PoliceOfficer, officer_person_id) is None:
        raise ValueError(
            f"Person {officer_person_id} is not registered as a police officer."
        )

    return get_or_create_link(
        db,
        AssignedTo,
        case_id=case.case_id,
        open_date=case.open_date,
        officer_person_id=officer_person_id,
    )


def unlink_officer_from_case(
    db: Session,
    case_id: int,
    officer_person_id: int,
    open_date: date | None = None,
) -> bool:
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


def assign_judge_to_trial(
    db: Session,
    case_id: int,
    trial_id: int,
    judge_person_id: int,
) -> Trial:
    trial = fetch_trial(db, case_id, trial_id)

    if db.get(Person, judge_person_id) is None:
        not_found("Person (judge)", judge_person_id)

    trial.judge_id = judge_person_id
    return trial


def link_suspect_evidence(
    db: Session,
    case: CaseDetail,
    suspect_person_id: int,
    evidence_id: int,
) -> LinkedTo:
    collected = (
        db.query(CollectedFor)
        .filter(
            CollectedFor.case_id == case.case_id,
            CollectedFor.open_date == case.open_date,
            CollectedFor.evidence_id == evidence_id,
        )
        .first()
    )
    if collected is None:
        raise ValueError(
            f"Evidence {evidence_id} is not collected for case {case.case_id}."
        )

    return get_or_create_link(
        db,
        LinkedTo,
        case_id=case.case_id,
        open_date=case.open_date,
        suspect_person_id=suspect_person_id,
        evidence_id=evidence_id,
    )


def next_trial_number(db: Session, case_id: int, open_date: date) -> int:
    db.query(CaseDetail).filter(
        CaseDetail.case_id == case_id, CaseDetail.open_date == open_date
    ).with_for_update().one()

    result = (
        db.query(func.max(Trial.trial_number))
        .filter(Trial.case_id == case_id, Trial.open_date == open_date)
        .scalar()
    )
    return (result or 0) + 1
