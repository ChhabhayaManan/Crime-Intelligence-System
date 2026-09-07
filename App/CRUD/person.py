"""
Functions for person and address CRUD operations in the Crime Intelligence System.
- create_address: Creates a new address.
- get_address: Fetches an address by id.
- update_address: Applies partial updates to an address.
- list_addresses: Lists addresses filtered by city and country, paginated.
- _build_role_details: Builds the per-role detail block for a person.
- _build_person_read: Converts a Person to a PersonRead with address and role details.
- create_person: Creates a person, reusing an existing address or creating one.
- resolve_person: Resolves a payload's person_id or inline person to a person id.
- _person_query: Builds the eager-loaded base query for person reads.
- get_person: Fetches a person by id.
- update_person: Applies partial updates to a person and their address.
- list_persons: Lists persons filtered by name search and role, paginated.
- get_person_cases: Returns every case a person is linked to, with their roles in each.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import or_, tuple_
from sqlalchemy.orm import Session, joinedload, selectinload

from App.db.models import (
    Address,
    CaseDetail,
    Criminal,
    Person,
    PoliceOfficer,
    Suspect,
    Victim,
    Witness,
)
from App.schema.core import (
    AddressCreate,
    AddressListResponse,
    AddressRead,
    AddressUpdate,
    CriminalDetails,
    PageMeta,
    PersonCaseLink,
    PersonCreate,
    PersonCreateResponse,
    PersonListResponse,
    PersonRead,
    PersonRoleDetails,
    PersonUpdate,
    PoliceOfficerDetails,
    SuspectDetails,
    VictimDetails,
    WitnessDetails,
)
from App.CRUD.common import build_person_summary, not_found, paginate, person_roles

_ROLE_JOINS = {
    "officer": PoliceOfficer,
    "suspect": Suspect,
    "victim": Victim,
    "witness": Witness,
    "criminal": Criminal,
}


def create_address(db: Session, payload: AddressCreate) -> AddressRead:
    addr = Address(
        street_address=payload.street_address,
        city=payload.city,
        state=payload.state,
        pin_code=payload.pin_code,
        country=payload.country,
    )
    db.add(addr)
    db.flush()
    return AddressRead.model_validate(addr)


def get_address(db: Session, address_id: int) -> AddressRead:
    addr = db.get(Address, address_id)
    if addr is None:
        not_found("Address", address_id)
    return AddressRead.model_validate(addr)


def update_address(db: Session, address_id: int, payload: AddressUpdate) -> AddressRead:
    addr = db.get(Address, address_id)
    if addr is None:
        not_found("Address", address_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(addr, field, value)

    db.flush()
    return AddressRead.model_validate(addr)


def list_addresses(
    db: Session,
    city: str | None = None,
    country: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> AddressListResponse:
    q = db.query(Address)
    if city:
        q = q.filter(Address.city.ilike(f"%{city}%"))
    if country:
        q = q.filter(Address.country.ilike(f"%{country}%"))

    items, total = paginate(q, page, page_size)
    return AddressListResponse(
        items=[AddressRead.model_validate(a) for a in items],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


def _build_role_details(person: Person) -> PersonRoleDetails:
    officer = person.police_profile
    suspect = person.suspect_profile
    victim = person.victim_profile
    witness = person.witness_profile
    criminal = person.criminal_profile

    return PersonRoleDetails(
        officer=(
            PoliceOfficerDetails(rank=officer.rank, department=officer.department)
            if officer
            else None
        ),
        suspect=(
            SuspectDetails(
                physical_description=suspect.physical_description,
                family_contact=suspect.family_contact,
                arrest_status=suspect.arrest_status,
            )
            if suspect
            else None
        ),
        victim=(
            VictimDetails(
                harm_details=victim.harm_details,
                family_contact=victim.family_contact,
            )
            if victim
            else None
        ),
        witness=(
            WitnessDetails(
                family_contact=witness.family_contact,
                testimony=witness.testimony,
            )
            if witness
            else None
        ),
        criminal=(
            CriminalDetails(c_family_contact=criminal.family_contact)
            if criminal
            else None
        ),
    )


def _build_person_read(person: Person) -> PersonRead:
    return PersonRead(
        person_id=person.person_id,
        gender=person.gender,
        birth_date=person.birth_date,
        first_name=person.first_name,
        middle_name=person.middle_name,
        last_name=person.last_name,
        occupation=person.occupation,
        contact_number=person.contact_number,
        address_id=person.address_id,
        address=AddressRead.model_validate(person.address) if person.address else None,
        roles=person_roles(person),
        role_details=_build_role_details(person),
    )


def create_person(db: Session, payload: PersonCreate) -> PersonCreateResponse:
    if payload.address_id is not None:
        if db.get(Address, payload.address_id) is None:
            not_found("Address", payload.address_id)
        address_id = payload.address_id
    elif payload.address is not None:
        address_id = create_address(db, payload.address).address_id
    else:
        raise ValueError("Provide either address_id or address.")

    person = Person(
        gender=payload.gender,
        birth_date=payload.birth_date,
        first_name=payload.first_name,
        middle_name=payload.middle_name,
        last_name=payload.last_name,
        occupation=payload.occupation,
        contact_number=payload.contact_number,
        address_id=address_id,
    )
    db.add(person)
    db.flush()
    return PersonCreateResponse(
        person_id=person.person_id,
        summary=build_person_summary(person),
    )


def resolve_person(db: Session, payload) -> int:
    if payload.person_id is not None:
        if db.get(Person, payload.person_id) is None:
            not_found("Person", payload.person_id)
        return payload.person_id

    if payload.person is None:
        raise ValueError("Provide exactly one of person_id or person.")

    return create_person(db, payload.person).person_id


def _person_query(db: Session):
    return db.query(Person).options(joinedload(Person.address))


def get_person(db: Session, person_id: int) -> PersonRead:
    person = _person_query(db).filter(Person.person_id == person_id).first()
    if person is None:
        not_found("Person", person_id)
    return _build_person_read(person)


def update_person(db: Session, person_id: int, payload: PersonUpdate) -> PersonRead:
    person = _person_query(db).filter(Person.person_id == person_id).first()
    if person is None:
        not_found("Person", person_id)

    data = payload.model_dump(exclude_unset=True)
    addr_payload = data.pop("address", None)
    new_addr_id = data.pop("address_id", None)

    if addr_payload is not None:
        if person.address_id is not None:
            addr = db.get(Address, person.address_id)
            if addr:
                for key, value in addr_payload.items():
                    setattr(addr, key, value)
        else:
            person.address_id = create_address(
                db, AddressCreate(**addr_payload)
            ).address_id
    elif new_addr_id is not None:
        if db.get(Address, new_addr_id) is None:
            not_found("Address", new_addr_id)
        person.address_id = new_addr_id

    for field, value in data.items():
        setattr(person, field, value)

    db.flush()
    return _build_person_read(person)


def list_persons(
    db: Session,
    query: str | None = None,
    role: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PersonListResponse:
    q = _person_query(db)

    if query:
        like = f"%{query}%"
        q = q.filter(
            or_(
                Person.first_name.ilike(like),
                Person.middle_name.ilike(like),
                Person.last_name.ilike(like),
            )
        )

    if role and role in _ROLE_JOINS:
        q = q.join(_ROLE_JOINS[role], isouter=False)

    items, total = paginate(q, page, page_size)

    return PersonListResponse(
        items=[build_person_summary(p) for p in items],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


def get_person_cases(db: Session, person_id: int) -> list[PersonCaseLink]:
    person = (
        db.query(Person)
        .options(
            selectinload(Person.reported_cases),
            selectinload(Person.police_profile).selectinload(PoliceOfficer.assignments),
            selectinload(Person.suspect_profile).selectinload(Suspect.involvements),
            selectinload(Person.victim_profile).selectinload(Victim.affected_cases),
            selectinload(Person.witness_profile).selectinload(
                Witness.testifies_in_cases
            ),
        )
        .filter(Person.person_id == person_id)
        .first()
    )
    if person is None:
        not_found("Person", person_id)

    case_roles: dict[tuple[int, date], set[str]] = {}

    def add(case_id: int, open_date: date, role: str) -> None:
        case_roles.setdefault((case_id, open_date), set()).add(role)

    for case in person.reported_cases:
        add(case.case_id, case.open_date, "reporter")
    if person.police_profile:
        for row in person.police_profile.assignments:
            add(row.case_id, row.open_date, "officer")
    if person.suspect_profile:
        for row in person.suspect_profile.involvements:
            add(row.case_id, row.open_date, "suspect")
    if person.victim_profile:
        for row in person.victim_profile.affected_cases:
            add(row.case_id, row.open_date, "victim")
    if person.witness_profile:
        for row in person.witness_profile.testifies_in_cases:
            add(row.case_id, row.open_date, "witness")

    if not case_roles:
        return []

    cases = (
        db.query(CaseDetail)
        .filter(tuple_(CaseDetail.case_id, CaseDetail.open_date).in_(list(case_roles)))
        .all()
    )
    case_map = {(c.case_id, c.open_date): c for c in cases}

    results: list[PersonCaseLink] = []
    for key, roles in sorted(case_roles.items()):
        case = case_map.get(key)
        if case:
            results.append(
                PersonCaseLink(
                    case_id=case.case_id,
                    open_date=case.open_date,
                    crime_type=case.crime_type,
                    status=case.case_status,
                    roles=sorted(roles),
                )
            )
    return results
