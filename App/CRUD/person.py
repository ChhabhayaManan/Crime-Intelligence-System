"""
person.py
---------
CRUD operations for Address and Person entities.

Functions
---------
Address
  create_address  – POST /addresses
  get_address     – GET  /addresses/{address_id}
  update_address  – PATCH /addresses/{address_id}
  list_addresses  – GET  /addresses

Person
  create_person   – POST /persons
  get_person      – GET  /persons/{person_id}
  update_person   – PATCH /persons/{person_id}
  list_persons    – GET  /persons
  get_person_cases – GET /persons/{person_id}/cases
"""

from __future__ import annotations
from datetime import date
from sqlalchemy import or_, tuple_
from sqlalchemy.orm import Session
from App.db.models import *
from App.schema.core import *
from App.CRUD.common import build_person_summary, next_id, not_found, paginate


# ---------------------------------------------------------------------------
# Address
# ---------------------------------------------------------------------------


def create_address(db: Session, payload: AddressCreate) -> AddressRead:
    """Insert a new address row and return its schema representation."""
    new_id = next_id(db, Address, "address_id")
    addr = Address(
        address_id=new_id,
        street_address=payload.street_address,
        city=payload.city,
        state=payload.state,
        pin_code=payload.pin_code,
        country=payload.country,
    )
    db.add(addr)
    db.commit()
    db.refresh(addr)
    return AddressRead.model_validate(addr)


def get_address(db: Session, address_id: int) -> AddressRead:
    """Fetch a single address by ID."""
    addr = db.get(Address, address_id)
    if addr is None:
        not_found("Address", address_id)
    return AddressRead.model_validate(addr)


def update_address(db: Session, address_id: int, payload: AddressUpdate) -> AddressRead:
    """Apply partial updates to an existing address."""
    addr = db.get(Address, address_id)
    if addr is None:
        not_found("Address", address_id)

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(addr, field, value)

    db.commit()
    db.refresh(addr)
    return AddressRead.model_validate(addr)


def list_addresses(
    db: Session,
    city: str | None = None,
    country: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> AddressListResponse:
    """Return a paginated list of addresses, with optional city / country filters."""
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


# ---------------------------------------------------------------------------
# Person helpers
# ---------------------------------------------------------------------------


def _build_role_details(person: Person) -> PersonRoleDetails:
    officer = (
        PoliceOfficerDetails(
            rank=person.police_profile.rank,
            department=person.police_profile.department,
        )
        if person.police_profile
        else None
    )
    suspect = (
        SuspectDetails(
            physical_description=person.suspect_profile.physical_description,
            family_contact=person.suspect_profile.family_contact,
            arrest_status=person.suspect_profile.arrest_status,
        )
        if person.suspect_profile
        else None
    )
    victim = (
        VictimDetails(
            harm_details=person.victim_profile.harm_details,
            family_contact=person.victim_profile.family_contact,
        )
        if person.victim_profile
        else None
    )
    witness = (
        WitnessDetails(
            family_contact=person.witness_profile.family_contact,
            testimony=person.witness_profile.testimony,
        )
        if person.witness_profile
        else None
    )
    criminal = (
        CriminalDetails(
            c_family_contact=person.criminal_profile.family_contact,
        )
        if person.criminal_profile
        else None
    )
    return PersonRoleDetails(
        officer=officer,
        suspect=suspect,
        victim=victim,
        witness=witness,
        criminal=criminal,
    )


def _build_person_read(person: Person) -> PersonRead:
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
        roles=roles,
        role_details=_build_role_details(person),
    )


# ---------------------------------------------------------------------------
# Person
# ---------------------------------------------------------------------------


def create_person(db: Session, payload: PersonCreate) -> PersonCreateResponse:
    """
    Create a Person row.

    If ``payload.address`` is an inline ``AddressCreate``, a new Address is
    inserted first.  If ``payload.address_id`` references an existing address
    that is used directly.
    """
    # Resolve address
    if payload.address_id is not None:
        if db.get(Address, payload.address_id) is None:
            not_found("Address", payload.address_id)
        address_id = payload.address_id
    else:
        # Inline address creation
        new_addr = create_address(db, payload.address)  # type: ignore[arg-type]
        address_id = new_addr.address_id

    new_id = next_id(db, Person, "person_id")
    person = Person(
        person_id=new_id,
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
    db.commit()
    db.refresh(person)

    return PersonCreateResponse(
        person_id=person.person_id,
        summary=build_person_summary(person),
    )


def get_person(db: Session, person_id: int) -> PersonRead:
    """Return the full details of a person by ID."""
    person = db.get(Person, person_id)
    if person is None:
        not_found("Person", person_id)
    return _build_person_read(person)  # type: ignore[arg-type]


def update_person(db: Session, person_id: int, payload: PersonUpdate) -> PersonRead:
    """Apply partial updates to a person record."""
    person = db.get(Person, person_id)
    if person is None:
        not_found("Person", person_id)

    data = payload.model_dump(exclude_none=True)

    # Handle address updates
    if "address" in data:
        addr_payload = data.pop("address")
        if person.address_id is not None:  # type: ignore[union-attr]
            # Update existing linked address
            addr = db.get(Address, person.address_id)  # type: ignore[union-attr]
            if addr:
                for k, v in addr_payload.items():
                    setattr(addr, k, v)
        else:
            # Create new address and link
            new_addr = create_address(db, AddressCreate(**addr_payload))
            person.address_id = new_addr.address_id  # type: ignore[union-attr]
    elif "address_id" in data:
        new_addr_id = data.pop("address_id")
        if db.get(Address, new_addr_id) is None:
            not_found("Address", new_addr_id)
        person.address_id = new_addr_id  # type: ignore[union-attr]

    for field, value in data.items():
        setattr(person, field, value)

    db.commit()
    db.refresh(person)
    return _build_person_read(person)  # type: ignore[return-value]


def list_persons(
    db: Session,
    query: str | None = None,
    role: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PersonListResponse:
    """
    Paginated list of persons.

    Supports free-text *query* (matches first/last/middle name) and *role*
    filter (officer / suspect / victim / witness / criminal).
    """
    q = db.query(Person)

    if query:
        like = f"%{query}%"
        q = q.filter(
            or_(
                Person.first_name.ilike(like),
                Person.middle_name.ilike(like),
                Person.last_name.ilike(like),
            )
        )

    _ROLE_JOINS = {
        "officer": PoliceOfficer,
        "suspect": Suspect,
        "victim": Victim,
        "witness": Witness,
        "criminal": Criminal,
    }

    if role and role in _ROLE_JOINS:
        role_model = _ROLE_JOINS[role]
        q = q.join(role_model, isouter=False)

    items, total = paginate(q, page, page_size)

    return PersonListResponse(
        items=[
            PersonSummary.model_validate(build_person_summary(p)) for p in items
        ],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


def get_person_cases(db: Session, person_id: int) -> list[dict]:
    """Return all cases linked to a person, with the role(s) they hold in each case."""
    person = db.get(Person, person_id)
    if person is None:
        not_found("Person", person_id)

    # Map (case_id, open_date) → set of roles
    case_roles: dict[tuple[int, date], set[str]] = {}

    def _add(case_id, open_date, role):
        key = (case_id, open_date)
        case_roles.setdefault(key, set()).add(role)

    for c in person.reported_cases:  # type: ignore[union-attr]
        _add(c.case_id, c.open_date, "reporter")

    if person.police_profile:
        for a in person.police_profile.assignments:
            _add(a.case_id, a.open_date, "officer")

    if person.suspect_profile:
        for inv in person.suspect_profile.involvements:
            _add(inv.case_id, inv.open_date, "suspect")

    if person.victim_profile:
        for ab in person.victim_profile.affected_cases:
            _add(ab.case_id, ab.open_date, "victim")

    if person.witness_profile:
        for ti in person.witness_profile.testifies_in_cases:
            _add(ti.case_id, ti.open_date, "witness")

    if not case_roles:
        return []

    pairs = list(case_roles.keys())
    cases = (
        db.query(CaseDetail)
        .filter(tuple_(CaseDetail.case_id, CaseDetail.open_date).in_(pairs))
        .all()
    )
    case_map = {(c.case_id, c.open_date): c for c in cases}

    results = []
    for (cid, odate), roles in sorted(case_roles.items()):
        case = case_map.get((cid, odate))
        if case:
            results.append(
                {
                    "case_id": case.case_id,
                    "open_date": case.open_date,
                    "crime_type": case.crime_type,
                    "status": case.case_status,
                    "roles": sorted(roles),
                }
            )
    return results
