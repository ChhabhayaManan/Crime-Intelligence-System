"""
witness.py
----------
CRUD operations for Witnesses and Testimonies.

Functions
---------
  add_case_witness      – POST /cases/{case_id}/witnesses
  list_case_witnesses   – GET  /cases/{case_id}/witnesses
  record_testimony      – POST /cases/{case_id}/witnesses/{witness_id}/testimony
  list_case_testimonies – GET  /cases/{case_id}/testimonies
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from App.db.models import (
    Person,
    PointedTo,
    Suspect,
    TestifiesIn,
    Witness,
)
from App.schema.case import (
    CaseWitnessCreateRequest,
    CaseWitnessCreateResponse,
    CaseWitnessListResponse,
    TestimonyRead,
    WitnessRead,
    WitnessTestimonyCreateRequest,
)
from App.CRUD.common import (
    build_person_summary,
    not_found,
    fetch_case,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _witness_read(w: Witness) -> WitnessRead:
    person = build_person_summary(w.person) if w.person else None
    return WitnessRead(
        witness_id=w.witness_person_id,
        person=person,
        family_contact=w.family_contact,
        statement=w.testimony,
    )


# ---------------------------------------------------------------------------
# Public CRUD
# ---------------------------------------------------------------------------

def add_case_witness(
    db: Session,
    case_id: int,
    payload: CaseWitnessCreateRequest,
    open_date: date | None = None,
) -> CaseWitnessCreateResponse:
    """Add a witness to a case (by existing person_id or inline PersonCreate). Creates Witness profile and TestifiesIn link."""
    case = fetch_case(db, case_id, open_date)

    # Resolve the person
    if payload.person_id is not None:
        person = db.get(Person, payload.person_id)
        if person is None:
            not_found("Person", payload.person_id)
    else:
        from App.CRUD.person import create_person
        result = create_person(db, payload.person)  # type: ignore[arg-type]
        person = db.get(Person, result.person_id)

    person_id: int = person.person_id  # type: ignore[union-attr]

    # Ensure Witness profile exists
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

    # Ensure TestifiesIn link
    ti = (
        db.query(TestifiesIn)
        .filter(
            TestifiesIn.case_id == case.case_id,
            TestifiesIn.open_date == case.open_date,
            TestifiesIn.witness_person_id == person_id,
        )
        .first()
    )
    if ti is None:
        ti = TestifiesIn(
            case_id=case.case_id,
            open_date=case.open_date,
            witness_person_id=person_id,
        )
        db.add(ti)

    db.commit()
    db.refresh(witness)

    wr = _witness_read(witness)
    return CaseWitnessCreateResponse(witness_id=person_id, witness=wr)


def list_case_witnesses(
    db: Session,
    case_id: int,
    open_date: date | None = None,
) -> CaseWitnessListResponse:
    """Return all witnesses in a case."""
    case = fetch_case(db, case_id, open_date)

    witnesses = [
        _witness_read(ti.witness)
        for ti in case.testifies_in_entries
        if ti.witness
    ]
    return CaseWitnessListResponse(
        case_id=case.case_id,
        open_date=case.open_date,
        items=witnesses,
    )


def record_testimony(
    db: Session,
    case_id: int,
    witness_id: int,
    payload: WitnessTestimonyCreateRequest,
    open_date: date | None = None,
) -> TestimonyRead:
    """Set witness testimony text and link named suspects via PointedTo rows."""
    case = fetch_case(db, case_id, open_date)

    witness = db.get(Witness, witness_id)
    if witness is None:
        raise ValueError(
            f"Person {witness_id} is not registered as a witness."
        )

    ti = (
        db.query(TestifiesIn)
        .filter(
            TestifiesIn.case_id == case.case_id,
            TestifiesIn.open_date == case.open_date,
            TestifiesIn.witness_person_id == witness_id,
        )
        .first()
    )
    if ti is None:
        raise ValueError(
            f"Witness {witness_id} is not linked to case {case_id}."
        )

    # Update testimony text
    witness.testimony = payload.testimony_text

    # Create PointedTo rows for each suspect
    for suspect_id in payload.pointed_suspects:
        s = db.get(Suspect, suspect_id)
        if s is None:
            raise ValueError(f"Person {suspect_id} is not registered as a suspect.")

        existing_pt = (
            db.query(PointedTo)
            .filter(
                PointedTo.case_id == case.case_id,
                PointedTo.open_date == case.open_date,
                PointedTo.witness_person_id == witness_id,
                PointedTo.suspect_person_id == suspect_id,
            )
            .first()
        )
        if not existing_pt:
            pt = PointedTo(
                case_id=case.case_id,
                open_date=case.open_date,
                witness_person_id=witness_id,
                suspect_person_id=suspect_id,
            )
            db.add(pt)

    db.commit()
    db.refresh(ti)

    pointed = [pt.suspect_person_id for pt in ti.pointed_to_entries]
    # Use synthetic id based on witness+case for stability
    testimony_id = hash((case.case_id, case.open_date, witness_id)) % 2**31

    return TestimonyRead(
        testimony_id=abs(testimony_id),
        witness_id=witness_id,
        case_id=case.case_id,
        testimony_text=witness.testimony or "",
        pointed_suspects=pointed,
    )


def list_case_testimonies(
    db: Session,
    case_id: int,
    open_date: date | None = None,
) -> list[TestimonyRead]:
    """Return all testimony records for a case."""
    case = fetch_case(db, case_id, open_date)

    result = []
    for ti in case.testifies_in_entries:
        w: Witness = ti.witness
        if w is None:
            continue
        pointed = [pt.suspect_person_id for pt in ti.pointed_to_entries]
        tid = abs(hash((ti.case_id, ti.open_date, ti.witness_person_id)) % 2**31)
        result.append(
            TestimonyRead(
                testimony_id=tid,
                witness_id=ti.witness_person_id,
                case_id=ti.case_id,
                testimony_text=w.testimony or "",
                pointed_suspects=pointed,
            )
        )
    return result
