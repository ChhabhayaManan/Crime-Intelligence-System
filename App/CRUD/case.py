"""
Functions for case CRUD operations in the Crime Intelligence System.
- _case_to_read: Converts a CaseDetail to a CaseRead with reporter and location.
- open_case: Creates a case and optionally assigns its first officer.
- get_case: Fetches one case by id and optional open_date.
- update_case: Applies partial updates to an open case.
- close_case: Marks a case closed and sets its end date.
- list_cases: Lists cases with filtering, sorting and pagination.
- get_case_details: Fetches a case with the selected related collections.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session, joinedload, selectinload

from App.db.models import (
    Address,
    AffectedBy,
    CaseDetail,
    CollectedFor,
    InvolvedIn,
    Suspect,
    TestifiesIn,
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
)
from App.schema.core import AddressRead, PageMeta
from App.CRUD.common import (
    assign_officer_to_case,
    build_person_summary,
    fetch_case,
    paginate,
)
from App.CRUD.evidence import ev_read
from App.CRUD.suspect import suspect_read
from App.CRUD.trial import trial_read
from App.CRUD.victim import victim_read
from App.CRUD.witness import testimony_read, witness_read

_CASE_READ_LOADS = (
    joinedload(CaseDetail.crime_location_address),
    joinedload(CaseDetail.reporting_person),
    selectinload(CaseDetail.assigned_to_entries),
)

_SORT_MAP = {
    "open_date": CaseDetail.open_date.asc(),
    "-open_date": CaseDetail.open_date.desc(),
    "crime_date": CaseDetail.crime_date.asc(),
    "-crime_date": CaseDetail.crime_date.desc(),
    "status": CaseDetail.case_status.asc(),
    "-status": CaseDetail.case_status.desc(),
}


def _case_to_read(case: CaseDetail) -> CaseRead:
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
        reporter=(
            build_person_summary(case.reporting_person)
            if case.reporting_person
            else None
        ),
        location=(
            AddressRead.model_validate(case.crime_location_address)
            if case.crime_location_address
            else None
        ),
        assigned_officer_ids=[a.officer_person_id for a in case.assigned_to_entries],
    )


def open_case(db: Session, payload: CaseOpenRequest) -> CaseOpenResponse:
    case = CaseDetail(
        open_date=payload.open_date or date.today(),
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
        assign_officer_to_case(
            db, case.case_id, payload.initial_officer_id, case.open_date
        )

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
    return _case_to_read(fetch_case(db, case_id, open_date, *_CASE_READ_LOADS))


def update_case(
    db: Session,
    case_id: int,
    payload: CaseUpdateRequest,
    open_date: date | None = None,
) -> CaseRead:
    case = fetch_case(db, case_id, open_date, *_CASE_READ_LOADS)

    if case.case_status == CaseStatus.CLOSED.value:
        raise ValueError("Cannot update a closed case. Use the /close endpoint.")

    given = payload.model_dump(exclude_unset=True)

    if payload.status is not None:
        if (
            payload.status == CaseStatus.CLOSED
            and payload.end_date is None
            and case.end_date is None
        ):
            case.end_date = date.today()
        case.case_status = payload.status.value

    if "summary" in given:
        case.complaint_detail = payload.summary
    if "crime_type" in given:
        case.crime_type = payload.crime_type
    if "location_id" in given:
        case.crime_location = payload.location_id
    if "reported_by" in given:
        case.person_id = payload.reported_by
    if "occurred_at" in given:
        case.crime_date = payload.occurred_at
    if "end_date" in given:
        case.end_date = payload.end_date

    if payload.assigned_officer_id is not None:
        assign_officer_to_case(db, case_id, payload.assigned_officer_id, case.open_date)

    db.flush()
    return _case_to_read(case)


def close_case(
    db: Session,
    case_id: int,
    payload: CaseCloseRequest,
    open_date: date | None = None,
) -> CaseCloseResponse:
    case = fetch_case(db, case_id, open_date, *_CASE_READ_LOADS)
    case.case_status = CaseStatus.CLOSED.value
    case.end_date = payload.closed_at or date.today()

    db.flush()
    return CaseCloseResponse(
        case_id=case.case_id,
        open_date=case.open_date,
        status=CaseStatus.CLOSED,
        end_date=case.end_date,
    )


def list_cases(db: Session, query: CaseListQuery) -> CaseListResponse:
    q = db.query(CaseDetail).options(joinedload(CaseDetail.crime_location_address))

    if query.crime_type:
        q = q.filter(CaseDetail.crime_type.ilike(f"%{query.crime_type}%"))
    if query.status:
        q = q.filter(CaseDetail.case_status == query.status.value)
    if query.from_date:
        q = q.filter(CaseDetail.open_date >= query.from_date)
    if query.to_date:
        q = q.filter(CaseDetail.open_date <= query.to_date)
    if query.city:
        q = q.join(Address, Address.address_id == CaseDetail.crime_location).filter(
            Address.city.ilike(f"%{query.city}%")
        )

    q = q.order_by(_SORT_MAP.get(query.sort.value, CaseDetail.open_date.desc()))

    items, total = paginate(q, query.page, query.page_size)

    return CaseListResponse(
        items=[
            CaseListItem(
                case_id=c.case_id,
                open_date=c.open_date,
                crime_date=c.crime_date,
                crime_type=c.crime_type,
                status=CaseStatus(c.case_status) if c.case_status else None,
                city=(
                    c.crime_location_address.city if c.crime_location_address else None
                ),
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
    case = fetch_case(
        db,
        case_id,
        open_date,
        *_CASE_READ_LOADS,
        selectinload(CaseDetail.collected_for_entries).joinedload(CollectedFor.evidence),
        selectinload(CaseDetail.trials),
        selectinload(CaseDetail.testifies_in_entries).joinedload(TestifiesIn.witness),
        selectinload(CaseDetail.testifies_in_entries).selectinload(
            TestifiesIn.pointed_to_entries
        ),
        selectinload(CaseDetail.involved_in_entries)
        .joinedload(InvolvedIn.suspect)
        .selectinload(Suspect.linked_evidence),
        selectinload(CaseDetail.affected_by_entries).joinedload(AffectedBy.victim),
    )
    included = set(include) if include else set(CaseInclude)

    return CaseDetailResponse(
        case=_case_to_read(case),
        included=list(included),
        evidence=(
            [
                ev_read(cf.evidence, cf.case_id, cf.open_date)
                for cf in case.collected_for_entries
            ]
            if CaseInclude.EVIDENCE in included
            else []
        ),
        witnesses=(
            [witness_read(e.witness) for e in case.testifies_in_entries if e.witness]
            if CaseInclude.WITNESSES in included
            else []
        ),
        suspects=(
            [suspect_read(e.suspect) for e in case.involved_in_entries if e.suspect]
            if CaseInclude.SUSPECTS in included
            else []
        ),
        victims=(
            [victim_read(e.victim) for e in case.affected_by_entries if e.victim]
            if CaseInclude.VICTIMS in included
            else []
        ),
        trials=(
            [trial_read(t) for t in case.trials]
            if CaseInclude.TRIALS in included
            else []
        ),
        testimonies=(
            [testimony_read(e) for e in case.testifies_in_entries]
            if CaseInclude.TESTIMONIES in included
            else []
        ),
    )
