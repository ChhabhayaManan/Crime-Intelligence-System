"""
Functions for case witness and testimony CRUD operations in the Crime Intelligence System.
- witness_read: Converts a Witness to a WitnessRead with person summary.
- testimony_read: Converts a TestifiesIn row to a TestimonyRead.
- add_case_witness: Links a person to a case as a witness.
- list_case_witnesses: Lists all witnesses testifying in a case.
- record_testimony: Stores a witness's testimony for a case and links the suspects they pointed to.
- list_case_testimonies: Lists every testimony recorded for a case.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session, selectinload

from App.db.models import CaseDetail, PointedTo, Suspect, TestifiesIn, Witness
from App.schema.case import (
    CaseWitnessCreateRequest,
    CaseWitnessCreateResponse,
    CaseWitnessListResponse,
    TestimonyRead,
    WitnessTestimonyCreateRequest,
    WitnessRead,
)
from App.CRUD.common import (
    build_person_summary,
    fetch_case,
    get_or_create_link,
)
from App.CRUD.person import resolve_person


def witness_read(witness: Witness) -> WitnessRead:
    return WitnessRead(
        witness_id=witness.witness_person_id,
        person=build_person_summary(witness.person) if witness.person else None,
        family_contact=witness.family_contact,
        statement=witness.testimony,
    )


def testimony_read(entry: TestifiesIn) -> TestimonyRead:
    return TestimonyRead(
        testimony_id=entry.witness_person_id,
        witness_id=entry.witness_person_id,
        case_id=entry.case_id,
        testimony_text=entry.testimony or "",
        pointed_suspects=[pt.suspect_person_id for pt in entry.pointed_to_entries],
    )


def add_case_witness(
    db: Session,
    case_id: int,
    payload: CaseWitnessCreateRequest,
    open_date: date | None = None,
) -> CaseWitnessCreateResponse:
    case = fetch_case(db, case_id, open_date)
    person_id = resolve_person(db, payload)

    witness = db.get(Witness, person_id)
    if witness is None:
        witness = Witness(
            witness_person_id=person_id,
            family_contact=payload.contact_info,
            testimony=payload.statement,
        )
        db.add(witness)
        db.flush()
    else:
        if payload.contact_info:
            witness.family_contact = payload.contact_info
        if payload.statement:
            witness.testimony = payload.statement

    get_or_create_link(
        db,
        TestifiesIn,
        case_id=case.case_id,
        open_date=case.open_date,
        witness_person_id=person_id,
    )
    db.flush()

    return CaseWitnessCreateResponse(
        witness_id=person_id,
        witness=witness_read(witness),
    )


def list_case_witnesses(
    db: Session,
    case_id: int,
    open_date: date | None = None,
) -> CaseWitnessListResponse:
    case = fetch_case(
        db,
        case_id,
        open_date,
        selectinload(CaseDetail.testifies_in_entries).joinedload(TestifiesIn.witness),
    )

    return CaseWitnessListResponse(
        case_id=case.case_id,
        open_date=case.open_date,
        items=[
            witness_read(entry.witness)
            for entry in case.testifies_in_entries
            if entry.witness
        ],
    )


def record_testimony(
    db: Session,
    case_id: int,
    witness_id: int,
    payload: WitnessTestimonyCreateRequest,
    open_date: date | None = None,
) -> TestimonyRead:
    case = fetch_case(db, case_id, open_date)

    if db.get(Witness, witness_id) is None:
        raise ValueError(f"Person {witness_id} is not registered as a witness.")

    entry = (
        db.query(TestifiesIn)
        .filter(
            TestifiesIn.case_id == case.case_id,
            TestifiesIn.open_date == case.open_date,
            TestifiesIn.witness_person_id == witness_id,
        )
        .first()
    )
    if entry is None:
        raise ValueError(f"Witness {witness_id} is not linked to case {case_id}.")

    entry.testimony = payload.testimony_text

    for suspect_id in payload.pointed_suspects:
        if db.get(Suspect, suspect_id) is None:
            raise ValueError(f"Person {suspect_id} is not registered as a suspect.")
        get_or_create_link(
            db,
            PointedTo,
            case_id=case.case_id,
            open_date=case.open_date,
            witness_person_id=witness_id,
            suspect_person_id=suspect_id,
        )

    db.flush()
    db.refresh(entry)
    return testimony_read(entry)


def list_case_testimonies(
    db: Session,
    case_id: int,
    open_date: date | None = None,
) -> list[TestimonyRead]:
    case = fetch_case(
        db,
        case_id,
        open_date,
        selectinload(CaseDetail.testifies_in_entries).selectinload(
            TestifiesIn.pointed_to_entries
        ),
    )
    return [testimony_read(entry) for entry in case.testifies_in_entries]
