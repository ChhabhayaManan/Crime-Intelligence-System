from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class SchemaModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="forbid")


class PageMeta(SchemaModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    total: int = Field(default=0, ge=0)


# --------------Address Schemas--------------
class AddressBase(SchemaModel):
    """Input: Base address fields."""
    street_address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=100)


class AddressCreate(AddressBase):
    pass


class AddressUpdate(AddressBase):
    pass


class AddressRead(AddressBase):
    """Response: Address with ID from database."""
    address_id: int = Field(..., gt=0)


# --------------Person Schemas--------------
class PersonBase(SchemaModel):
    """Input: Base person fields."""
    gender: str | None = Field(default=None, min_length=1, max_length=1)
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
    """Input: Create person with address reference or inline address."""
    address_id: int | None = Field(default=None, gt=0)
    address: AddressCreate | None = None

    @model_validator(mode="after")
    def validate_address_source(self) -> PersonCreate:
        if self.address_id is None and self.address is None:
            raise ValueError("Provide either address_id or address.")
        if self.address_id is not None and self.address is not None:
            raise ValueError("Provide only one of address_id or address.")
        return self


class PersonUpdate(SchemaModel):
    """Input: Update person fields and address."""
    gender: str | None = Field(default=None, min_length=1, max_length=1)
    birth_date: date | None = None
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    occupation: str | None = Field(default=None, max_length=100)
    contact_number: str | None = Field(default=None, max_length=15)
    address_id: int | None = Field(default=None, gt=0)
    address: AddressUpdate | None = None

    @model_validator(mode="after")
    def validate_address_source(self) -> PersonUpdate:
        if self.address_id is not None and self.address is not None:
            raise ValueError("Provide either address_id or address, not both.")
        return self

class PersonRole(str, Enum):
    """Input: Enum for person role types."""
    OFFICER = "officer"
    SUSPECT = "suspect"
    VICTIM = "victim"
    WITNESS = "witness"
    CRIMINAL = "criminal"


class PersonRoleDetails(SchemaModel):
    """Response: Details for each role type."""
    officer: PoliceOfficerDetails | None = None
    suspect: SuspectDetails | None = None
    victim: VictimDetails | None = None
    witness: WitnessDetails | None = None
    criminal: CriminalDetails | None = None


class PersonSummary(SchemaModel):
    """Response: Basic person info with active roles."""
    person_id: int = Field(..., gt=0)
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    full_name: str | None = None
    address_id: int | None = Field(default=None, gt=0)
    roles: list[PersonRole] = Field(default_factory=list)


class PersonRead(PersonBase):
    """Response: Complete person data with address and role details."""
    person_id: int = Field(..., gt=0)
    address_id: int | None = Field(default=None, gt=0)
    address: AddressRead | None = None
    linked_addresses: list[AddressRead] = Field(default_factory=list)
    roles: list[PersonRole] = Field(default_factory=list)
    role_details: PersonRoleDetails = Field(default_factory=PersonRoleDetails)


class PersonCreateResponse(SchemaModel):
    """Response: Created person with summary."""
    person_id: int = Field(..., gt=0)
    summary: PersonSummary


class PersonListItem(PersonSummary):
    pass


class PersonListResponse(SchemaModel):
    """Response: Paginated person list."""
    items: list[PersonListItem] = Field(default_factory=list)
    meta: PageMeta = Field(default_factory=PageMeta)

#--------------Person Role Schemas--------------
class PoliceOfficerDetails(SchemaModel):
    """Input: Officer rank and department info."""
    rank: str | None = Field(default=None, max_length=50)
    department: str | None = Field(default=None, max_length=100)


class CriminalDetails(SchemaModel):
    """Input: Criminal family contact info."""
    c_family_contact: str | None = Field(default=None, max_length=15)


class SuspectDetails(SchemaModel):
    """Input: Suspect physical description and arrest status."""
    physical_description: str | None = Field(default=None, max_length=255)
    family_contact: str | None = Field(default=None, max_length=15)
    arrest_status: str | None = Field(default=None, max_length=50)


class VictimDetails(SchemaModel):
    """Input: Victim harm details and family contact."""
    harm_details: str | None = Field(default=None, max_length=255)
    family_contact: str | None = Field(default=None, max_length=15)


class WitnessDetails(SchemaModel):
    """Input: Witness testimony and contact info."""
    family_contact: str | None = Field(default=None, max_length=15)
    testimony: str | None = Field(default=None, max_length=255)


# ── Auth Schemas ─────────────────────────────────────────────────────────────

class UserRegisterRequest(SchemaModel):
    """Input: New user registration payload."""
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    mobile_number: str | None = Field(default=None, max_length=15)
    password: str = Field(..., min_length=8, max_length=200)
    confirm_password: str = Field(..., min_length=8, max_length=200)

    @model_validator(mode="after")
    def passwords_match(self) -> "UserRegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password do not match.")
        return self


class UserLoginRequest(SchemaModel):
    """Input: Login credentials."""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)


class ChangePasswordRequest(SchemaModel):
    """Input: Change password payload."""
    username: str = Field(..., min_length=1, max_length=100)
    current_password: str = Field(..., min_length=1, max_length=200)
    new_password: str = Field(..., min_length=8, max_length=200)


class TokenOut(SchemaModel):
    """Response: JWT access token."""
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class UserOut(SchemaModel):
    """Response: Safe user representation (no password)."""
    user_id: int
    username: str
    email: EmailStr
    mobile_number: str | None = None
    role: str
    is_active: bool


__all__ = [
    "SchemaModel",
    "PageMeta",
    "PersonRole",
    "AddressBase",
    "AddressCreate",
    "AddressUpdate",
    "AddressRead",
    "PersonBase",
    "PersonCreate",
    "PersonUpdate",
    "PersonSummary",
    "PersonRead",
    "PersonCreateResponse",
    "PersonListItem",
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
    "UserOut",
]
