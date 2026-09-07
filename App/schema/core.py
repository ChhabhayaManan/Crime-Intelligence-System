from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

GENDER_PATTERN = "^[MFOU]$"

T = TypeVar("T")


class SchemaModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, extra="forbid"
    )


class NormalizedStrEnum(str, Enum):
    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            normalized = value.strip().lower()
            for member in cls:
                if member.value == normalized:
                    return member
        return None


class PageParams(SchemaModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class PageMeta(PageParams):
    total: int = Field(default=0, ge=0)


class MessageResponse(SchemaModel):
    detail: str


class DateRangeQuery(SchemaModel):
    from_date: date | None = Field(default=None, alias="from")
    to_date: date | None = Field(default=None, alias="to")

    @model_validator(mode="after")
    def validate_date_range(self) -> DateRangeQuery:
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValueError("from_date cannot be later than to_date.")
        return self


class ListResponse(SchemaModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    meta: PageMeta = Field(default_factory=PageMeta)


class CaseScopedList(SchemaModel, Generic[T]):
    case_id: int = Field(..., gt=0)
    open_date: date
    items: list[T] = Field(default_factory=list)


class AddressBase(SchemaModel):
    street_address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    pin_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=100)


class AddressCreate(AddressBase):
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    pin_code: str = Field(..., max_length=20)
    country: str = Field(..., max_length=100)


class AddressUpdate(AddressBase):
    pass


class AddressRead(AddressBase):
    address_id: int = Field(..., gt=0)


class AddressListResponse(ListResponse[AddressRead]):
    pass


class PoliceOfficerDetails(SchemaModel):
    rank: str | None = Field(default=None, max_length=50)
    department: str | None = Field(default=None, max_length=100)


class CriminalDetails(SchemaModel):
    c_family_contact: str | None = Field(default=None, max_length=15)


class SuspectDetails(SchemaModel):
    physical_description: str | None = Field(default=None, max_length=255)
    family_contact: str | None = Field(default=None, max_length=15)
    arrest_status: str | None = Field(default=None, max_length=50)


class VictimDetails(SchemaModel):
    harm_details: str | None = Field(default=None, max_length=255)
    family_contact: str | None = Field(default=None, max_length=15)


class WitnessDetails(SchemaModel):
    family_contact: str | None = Field(default=None, max_length=15)
    testimony: str | None = Field(default=None, max_length=255)


class PersonRole(str, Enum):
    OFFICER = "officer"
    SUSPECT = "suspect"
    VICTIM = "victim"
    WITNESS = "witness"
    CRIMINAL = "criminal"


class PersonRoleDetails(SchemaModel):
    officer: PoliceOfficerDetails | None = None
    suspect: SuspectDetails | None = None
    victim: VictimDetails | None = None
    witness: WitnessDetails | None = None
    criminal: CriminalDetails | None = None


class PersonBase(SchemaModel):
    gender: str | None = Field(default=None, pattern=GENDER_PATTERN)
    birth_date: date | None = None
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    occupation: str | None = Field(default=None, max_length=100)
    contact_number: str | None = Field(default=None, max_length=15)

    @model_validator(mode="after")
    def validate_birth_date(self) -> PersonBase:
        if self.birth_date is not None and self.birth_date > datetime.now().date():
            raise ValueError("Birth date cannot be in the future.")
        return self


class PersonCreate(PersonBase):
    address_id: int | None = Field(default=None, gt=0)
    address: AddressCreate | None = None

    @model_validator(mode="after")
    def validate_address_source(self) -> PersonCreate:
        if self.address_id is None and self.address is None:
            raise ValueError("Provide either address_id or address.")
        if self.address_id is not None and self.address is not None:
            raise ValueError("Provide only one of address_id or address.")
        return self


class PersonUpdate(PersonBase):
    address_id: int | None = Field(default=None, gt=0)
    address: AddressUpdate | None = None

    @model_validator(mode="after")
    def validate_address_source(self) -> PersonUpdate:
        if self.address_id is not None and self.address is not None:
            raise ValueError("Provide either address_id or address, not both.")
        return self


class PersonSummary(SchemaModel):
    person_id: int = Field(..., gt=0)
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    full_name: str | None = None
    address_id: int | None = Field(default=None, gt=0)
    roles: list[PersonRole] = Field(default_factory=list)


class PersonRead(PersonBase):
    person_id: int = Field(..., gt=0)
    address_id: int | None = Field(default=None, gt=0)
    address: AddressRead | None = None
    roles: list[PersonRole] = Field(default_factory=list)
    role_details: PersonRoleDetails = Field(default_factory=PersonRoleDetails)

class PersonCreateResponse(SchemaModel):
    person_id: int = Field(..., gt=0)
    summary: PersonSummary


class PersonCaseLink(SchemaModel):
    case_id: int = Field(..., gt=0)
    open_date: date
    crime_type: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=10)
    roles: list[str] = Field(default_factory=list)

class PersonListResponse(ListResponse[PersonSummary]):
    pass

class UserRegisterRequest(SchemaModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    mobile_number: str | None = Field(default=None, max_length=15)
    password: str = Field(..., min_length=8, max_length=200)
    confirm_password: str = Field(..., min_length=8, max_length=200)

    @model_validator(mode="after")
    def passwords_match(self) -> UserRegisterRequest:
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password do not match.")
        return self

class UserLoginRequest(SchemaModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)

class ChangePasswordRequest(SchemaModel):
    username: str = Field(..., min_length=1, max_length=100)
    current_password: str = Field(..., min_length=1, max_length=200)
    new_password: str = Field(..., min_length=8, max_length=200)

class TokenOut(SchemaModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime

class TokenRefreshRequest(SchemaModel):
    refresh_token: str

class TokenRefreshOut(SchemaModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime

class UserOut(SchemaModel):
    user_id: int
    username: str
    email: EmailStr
    mobile_number: str | None = None


__all__ = [
    "GENDER_PATTERN",
    "SchemaModel",
    "NormalizedStrEnum",
    "PageParams",
    "PageMeta",
    "DateRangeQuery",
    "ListResponse",
    "CaseScopedList",
    "PersonRole",
    "AddressBase",
    "AddressCreate",
    "AddressUpdate",
    "AddressRead",
    "AddressListResponse",
    "PersonBase",
    "PersonCreate",
    "PersonUpdate",
    "PersonSummary",
    "PersonRead",
    "PersonCreateResponse",
    "PersonCaseLink",
    "PersonListResponse",
    "PersonRoleDetails",
    "PoliceOfficerDetails",
    "CriminalDetails",
    "SuspectDetails",
    "VictimDetails",
    "WitnessDetails",
    "UserRegisterRequest",
    "UserLoginRequest",
    "ChangePasswordRequest",
    "TokenOut",
    "TokenRefreshRequest",
    "TokenRefreshOut",
    "UserOut",
]
