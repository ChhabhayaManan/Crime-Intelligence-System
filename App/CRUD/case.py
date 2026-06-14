"""
case.py
-------
CRUD operations for Case lifecycle.

Functions
---------
  open_case        – POST /cases
  get_case         – GET  /cases/{case_id}
  update_case      – PATCH /cases/{case_id}
  close_case       – PATCH /cases/{case_id}/close
  list_cases       – GET  /cases
  get_case_details – GET  /cases/{case_id}/details  (combined)
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session
from App.db.models import (
    Address,
    AffectedBy,
    CaseDetail,
    CollectedFor,
    Evidence,
    InvolvedIn,
    Suspect,
    TestifiesIn,
    Victim,
    Witness,
)
from App.schema.case import (
    CaseCloseRequest,
    CaseCloseResponse,
    CaseDetailResponse,
    CaseInclude,
    CaseListItem,
    CaseListQuery,
    CaseListResponse,
    CaseOpenRequest,
    CaseOpenResponse,
    CaseRead,
    CaseStatus,
    CaseUpdateRequest,
    EvidenceRead,
    SuspectRead,
    SuspectStatus,
    TestimonyRead,
    VictimRead,
    WitnessRead,
)
from App.schema.core import AddressRead, PageMeta
from App.CRUD.common import (
    assign_officer_to_case,
    build_person_summary,
    next_id,
    not_found,
    paginate,
    fetch_case,
)
from App.CRUD.trial import trial_read

# ---------------------------------------------------------------------------
# Internal mappers
# ---------------------------------------------------------------------------

def _case_to_read(case: CaseDetail) -> CaseRead:
    officer_ids = [a.officer_person_id for a in case.assigned_to_entries]
    reporter = (
        build_person_summary(case.reporting_person)
        if case.reporting_person
        else None
    )
    location = (
        AddressRead.model_validate(case.crime_location_address)
        if case.crime_location_address
        else None
    )
    return CaseRead(
        case_id=case.case_id,
        open_date=case.open_date,
        crime_date=case.crime_date,
        end_date=case.end_date,
        summary=case.complaint_detail,
        crime_type=case.crime_type,
        location_id=case.crime_location,
        status=CaseStatus(case.case_status) if case.case_status else None,
        reported_by=case.person_id,
        reporter=reporter,
        location=location,
        assigned_officer_ids=officer_ids,
    )


def _evidence_row(cf: CollectedFor) -> EvidenceRead:
    ev: Evidence = cf.evidence
    return EvidenceRead(
        evidence_id=ev.evidence_id,
        case_id=cf.case_id,
        open_date=cf.open_date,
        description=ev.description,
        collection_date=ev.collection_date,
        location_id=ev.location_id,
        evidence_type=None,
        collected_by=None,
    )


def _suspect_row(inv: InvolvedIn) -> SuspectRead:
    s: Suspect = inv.suspect
    linked_ev = [lt.evidence_id for lt in s.linked_evidence]
    person = build_person_summary(s.person) if s.person else None
    return SuspectRead(
        suspect_id=s.suspect_person_id,
        person=person,
        physical_description=s.physical_description,
        family_contact=s.family_contact,
        arrest_status=SuspectStatus(s.arrest_status) if s.arrest_status else None,
        reason=None,
        linked_evidence_ids=linked_ev,
    )


def _victim_row(ab: AffectedBy) -> VictimRead:
    v: Victim = ab.victim
    person = build_person_summary(v.person) if v.person else None
    return VictimRead(
        victim_id=v.victim_person_id,
        person=person,
        harm_details=v.harm_details,
        family_contact=v.family_contact,
    )


def _witness_row(ti: TestifiesIn) -> WitnessRead:
    w: Witness = ti.witness
    person = build_person_summary(w.person) if w.person else None
    return WitnessRead(
        witness_id=w.witness_person_id,
        person=person,
        family_contact=w.family_contact,
        statement=w.testimony,
    )


def _testimony_rows(case: CaseDetail) -> list[TestimonyRead]:
    return [
        TestimonyRead(
            testimony_id=tid,
            witness_id=ti.witness_person_id,
            case_id=ti.case_id,
            testimony_text=ti.witness.testimony or "",
            pointed_suspects=[pt.suspect_person_id for pt in ti.pointed_to_entries],
        )
        for tid, ti in enumerate(case.testifies_in_entries, start=1)
    ]


# ---------------------------------------------------------------------------
# Public CRUD functions
# ---------------------------------------------------------------------------

def open_case(db: Session, payload: CaseOpenRequest) -> CaseOpenResponse:
    """Create a new CaseDetail row and optionally assign an initial officer."""
    open_date = payload.open_date or date.today()
    new_id = next_id(db, CaseDetail, "case_id")

    case = CaseDetail(
        case_id=new_id,
        open_date=open_date,
        crime_date=payload.occurred_at,
        complaint_detail=payload.summary,
        crime_type=payload.crime_type,
        crime_location=payload.location_id,
        person_id=payload.reported_by,
        case_status=CaseStatus.OPEN.value,
    )
    db.add(case)
    db.flush()

    if payload.initial_officer_id:
        assign_officer_to_case(db, new_id, payload.initial_officer_id, open_date)

    db.commit()
    return CaseOpenResponse(
        case_id=case.case_id,
        open_date=case.open_date,
        status=CaseStatus.OPEN,
        summary=case.complaint_detail,
    )


def get_case(
    db: Session,
    case_id: int,
    open_date: date | None = None,
) -> CaseRead:
    """Fetch a single case's read representation."""
    case = fetch_case(db, case_id, open_date)
    return _case_to_read(case)


def update_case(
    db: Session,
    case_id: int,
    payload: CaseUpdateRequest,
    open_date: date | None = None,
) -> CaseRead:
    """Partially update a case record."""
    case = fetch_case(db, case_id, open_date)

    if payload.summary is not None:
        case.complaint_detail = payload.summary
    if payload.crime_type is not None:
        case.crime_type = payload.crime_type
    if payload.location_id is not None:
        case.crime_location = payload.location_id
    if payload.reported_by is not None:
        case.person_id = payload.reported_by
    if payload.occurred_at is not None:
        case.crime_date = payload.occurred_at
    if payload.status is not None:
        case.case_status = payload.status.value
    if payload.end_date is not None:
        case.end_date = payload.end_date

    if payload.assigned_officer_id is not None:
        assign_officer_to_case(db, case_id, payload.assigned_officer_id, case.open_date)

    db.commit()
    db.refresh(case)
    return _case_to_read(case)


def close_case(
    db: Session,
    case_id: int,
    payload: CaseCloseRequest,
    open_date: date | None = None,
) -> CaseCloseResponse:
    """Close a case by setting status to CLOSED and recording end_date."""
    case = fetch_case(db, case_id, open_date)
    case.case_status = CaseStatus.CLOSED.value
    case.end_date = payload.closed_at or date.today()
    if payload.closing_summary:
        case.complaint_detail = payload.closing_summary

    db.commit()
    db.refresh(case)
    return CaseCloseResponse(
        case_id=case.case_id,
        open_date=case.open_date,
        status=CaseStatus.CLOSED,
        end_date=case.end_date,
        closing_summary=case.complaint_detail,
    )


def list_cases(db: Session, query: CaseListQuery) -> CaseListResponse:
    """Return a filtered, sorted, paginated list of cases."""
    q = db.query(CaseDetail)

    if query.crime_type:
        q = q.filter(CaseDetail.crime_type.ilike(f"%{query.crime_type}%"))
    if query.status:
        q = q.filter(CaseDetail.case_status == query.status.value)

    if query.from_date:
        q = q.filter(CaseDetail.open_date >= query.from_date)
    if query.to_date:
        q = q.filter(CaseDetail.open_date <= query.to_date)

    if query.city:
        q = q.join(Address, Address.address_id == CaseDetail.crime_location, isouter=True)
        q = q.filter(Address.city.ilike(f"%{query.city}%"))

    # Sorting
    sort_map = {
        "open_date": CaseDetail.open_date.asc(),
        "-open_date": CaseDetail.open_date.desc(),
        "crime_date": CaseDetail.crime_date.asc(),
        "-crime_date": CaseDetail.crime_date.desc(),
        "status": CaseDetail.case_status.asc(),
        "-status": CaseDetail.case_status.desc(),
    }
    q = q.order_by(sort_map.get(query.sort.value, CaseDetail.open_date.desc()))

    items, total = paginate(q, query.page, query.page_size)

    return CaseListResponse(
        items=[
            CaseListItem(
                case_id=c.case_id,
                open_date=c.open_date,
                crime_date=c.crime_date,
                crime_type=c.crime_type,
                status=CaseStatus(c.case_status) if c.case_status else None,
                city=c.crime_location_address.city if c.crime_location_address else None,
            )
            for c in items
        ],
        meta=PageMeta(page=query.page, page_size=query.page_size, total=total),
    )


def get_case_details(
    db: Session,
    case_id: int,
    include: list[CaseInclude] | None = None,
    open_date: date | None = None,
) -> CaseDetailResponse:
    """Return a case with all related sub-entities (filtered by include list if provided)."""
    case = fetch_case(db, case_id, open_date)
    include_set = set(include) if include else set(CaseInclude)

    evidence = (
        [_evidence_row(cf) for cf in case.collected_for_entries]
        if CaseInclude.EVIDENCE in include_set
        else []
    )
    witnesses = (
        [_witness_row(ti) for ti in case.testifies_in_entries]
        if CaseInclude.WITNESSES in include_set
        else []
    )
    suspects = (
        [_suspect_row(inv) for inv in case.involved_in_entries]
        if CaseInclude.SUSPECTS in include_set
        else []
    )
    victims = (
        [_victim_row(ab) for ab in case.affected_by_entries]
        if CaseInclude.VICTIMS in include_set
        else []
    )
    trials = (
        [trial_read(t) for t in case.trials]
        if CaseInclude.TRIALS in include_set
        else []
    )
    testimonies = (
        _testimony_rows(case)
        if CaseInclude.TESTIMONIES in include_set
        else []
    )

    return CaseDetailResponse(
        case=_case_to_read(case),
        included=list(include_set),
        evidence=evidence,
        witnesses=witnesses,
        suspects=suspects,
        victims=victims,
        trials=trials,
        testimonies=testimonies,
    )
