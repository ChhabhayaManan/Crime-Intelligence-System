from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import Field, PositiveInt, computed_field, model_validator

from App.schema.core import *


class CaseStatus(NormalizedStrEnum):
    OPEN = "open"
    CLOSED = "closed"
    ON_HOLD = "on_hold"


class CaseInclude(str, Enum):
    EVIDENCE = "evidence"
    WITNESSES = "witnesses"
    SUSPECTS = "suspects"
    TRIALS = "trials"
    VICTIMS = "victims"
    TESTIMONIES = "testimonies"


class SuspectStatus(NormalizedStrEnum):
    WANTED = "wanted"
    ARRESTED = "arrested"
    RELEASED = "released"


class CaseSortBy(str, Enum):
    OPEN_DATE_ASC = "open_date"
    OPEN_DATE_DESC = "-open_date"
    CRIME_DATE_ASC = "crime_date"
    CRIME_DATE_DESC = "-crime_date"
    STATUS_ASC = "status"
    STATUS_DESC = "-status"


class PersonReferenceInput(SchemaModel):
    person_id: int | None = Field(default=None, gt=0)
    person: PersonCreate | None = None

    @model_validator(mode="after")
    def validate_person_reference(self) -> PersonReferenceInput:
        if (self.person_id is not None) == (self.person is not None):
            raise ValueError("Provide exactly one of person_id or person.")
        return self


class CaseOpenRequest(SchemaModel):
    summary: str = Field(
        ..., max_length=255, description="Maps to case_details.complaint_detail."
    )
    crime_type: str = Field(..., max_length=50)
    location_id: int = Field(
        ..., gt=0, description="Maps to case_details.crime_location."
    )
    reported_by: int = Field(..., gt=0, description="Maps to case_details.personid.")
    initial_officer_id: int | None = Field(default=None, gt=0)
    occurred_at: date = Field(..., description="Maps to case_details.crime_date.")
    open_date: date | None = None

    @model_validator(mode="after")
    def validate_crime_before_open(self) -> CaseOpenRequest:
        if self.open_date and self.occurred_at > self.open_date:
            raise ValueError("occurred_at cannot be later than open_date.")
        return self


class CaseOpenResponse(SchemaModel):
    case_id: int = Field(..., gt=0)
    open_date: date
    status: CaseStatus = CaseStatus.OPEN
    summary: str | None = Field(default=None, max_length=255)


class CaseUpdateRequest(SchemaModel):
    summary: str | None = Field(default=None, max_length=255)
    crime_type: str | None = Field(default=None, max_length=50)
    location_id: int | None = Field(default=None, gt=0)
    reported_by: int | None = Field(default=None, gt=0)
    occurred_at: date | None = None
    status: CaseStatus | None = None
    assigned_officer_id: int | None = Field(default=None, gt=0)
    end_date: date | None = None


class CaseCloseRequest(SchemaModel):
    closed_at: date | None = None


class CaseCloseResponse(SchemaModel):
    case_id: int = Field(..., gt=0)
    open_date: date
    status: CaseStatus = CaseStatus.CLOSED
    end_date: date | None = None


class CaseRead(SchemaModel):
    case_id: int = Field(..., gt=0)
    open_date: date
    crime_date: date | None = None
    end_date: date | None = None
    summary: str | None = Field(
        default=None, max_length=255, description="Case complaint/summary text."
    )
    crime_type: str | None = Field(default=None, max_length=50)
    location_id: int | None = Field(default=None, gt=0)
    status: CaseStatus | None = None
    reported_by: int | None = Field(default=None, gt=0)
    reporter: PersonSummary | None = None
    location: AddressRead | None = None
    assigned_officer_ids: list[int] = Field(default_factory=list)


class CaseListQuery(DateRangeQuery, PageParams):
    crime_type: str | None = Field(default=None, max_length=50)
    city: str | None = Field(default=None, max_length=100)
    status: CaseStatus | None = None
    sort: CaseSortBy = CaseSortBy.OPEN_DATE_DESC


class CaseListItem(SchemaModel):
    case_id: int = Field(..., gt=0)
    open_date: date
    crime_date: date | None = None
    crime_type: str | None = Field(default=None, max_length=50)
    status: CaseStatus | None = None
    city: str | None = Field(default=None, max_length=100)


class CaseListResponse(ListResponse[CaseListItem]):
    pass


class CaseEvidenceCreateRequest(SchemaModel):
    description: str | None = Field(default=None, max_length=255)
    collected_at: date | None = Field(
        default=None, description="Maps to evidence.collection_date."
    )
    location_id: int | None = Field(
        default=None, gt=0, description="Maps to evidence.location_id."
    )


class CaseEvidenceUpdateRequest(SchemaModel):
    description: str | None = Field(default=None, max_length=255)
    collected_at: date | None = Field(
        default=None, description="Maps to evidence.collection_date."
    )
    location_id: int | None = Field(default=None, gt=0)


class EvidenceRead(SchemaModel):
    evidence_id: int = Field(..., gt=0)
    case_id: int = Field(..., gt=0)
    open_date: date
    description: str | None = Field(default=None, max_length=255)
    collection_date: date | None = None
    location_id: int | None = Field(default=None, gt=0)
    file_key: str | None = None
    file_content_type: str | None = None
    file_size: int | None = Field(default=None, ge=0)


class CaseEvidenceCreateResponse(SchemaModel):
    evidence_id: int = Field(..., gt=0)
    evidence: EvidenceRead


class CaseEvidenceListResponse(CaseScopedList[EvidenceRead]):
    pass


class CaseWitnessCreateRequest(PersonReferenceInput):
    contact_info: str | None = Field(
        default=None,
        max_length=15,
        description="Maps to witness.family_contact.",
    )
    statement: str | None = Field(
        default=None, max_length=255, description="Maps to witness.testimony."
    )


class WitnessRead(SchemaModel):
    witness_id: int = Field(
        ..., gt=0, description="Person id used as witness primary key."
    )
    person: PersonSummary | None = None
    family_contact: str | None = Field(default=None, max_length=15)
    statement: str | None = Field(default=None, max_length=255)


class CaseWitnessCreateResponse(SchemaModel):
    witness_id: int = Field(..., gt=0)
    witness: WitnessRead


class CaseWitnessListResponse(CaseScopedList[WitnessRead]):
    pass


class WitnessTestimonyCreateRequest(SchemaModel):
    testimony_text: str = Field(..., max_length=255)
    pointed_suspects: list[PositiveInt] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pointed_suspects(self) -> WitnessTestimonyCreateRequest:
        if len(set(self.pointed_suspects)) != len(self.pointed_suspects):
            raise ValueError("pointed_suspects contains duplicate person ids.")
        return self


class TestimonyRead(SchemaModel):
    testimony_id: int = Field(..., gt=0)
    witness_id: int = Field(..., gt=0)
    case_id: int = Field(..., gt=0)
    testimony_text: str = Field(..., max_length=255)
    pointed_suspects: list[int] = Field(default_factory=list)


class CaseSuspectCreateRequest(PersonReferenceInput):
    evidence_ids: list[PositiveInt] = Field(default_factory=list)


class SuspectRead(SchemaModel):
    suspect_id: int = Field(
        ..., gt=0, description="Person id used as suspect primary key."
    )
    person: PersonSummary | None = None
    physical_description: str | None = Field(default=None, max_length=255)
    family_contact: str | None = Field(default=None, max_length=15)
    arrest_status: SuspectStatus | None = None
    linked_evidence_ids: list[int] = Field(default_factory=list)


class CaseSuspectCreateResponse(SchemaModel):
    suspect_id: int = Field(..., gt=0)
    suspect: SuspectRead


class CaseSuspectUpdateResponse(CaseSuspectCreateResponse):
    pass

class CaseSuspectListResponse(CaseScopedList[SuspectRead]):
    pass


class CaseSuspectUpdateRequest(SchemaModel):
    arrest_status: SuspectStatus | None = None
    physical_description: str | None = Field(default=None, max_length=255)
    family_contact: str | None = Field(default=None, max_length=15)


class CaseVictimCreateRequest(PersonReferenceInput):
    harm_details: str | None = Field(default=None, max_length=255)
    family_contact: str | None = Field(default=None, max_length=15)


class VictimRead(SchemaModel):
    victim_id: int = Field(
        ..., gt=0, description="Person id used as victim primary key."
    )
    person: PersonSummary | None = None
    harm_details: str | None = Field(default=None, max_length=255)
    family_contact: str | None = Field(default=None, max_length=15)


class CaseVictimCreateResponse(SchemaModel):
    victim_id: int = Field(..., gt=0)
    victim: VictimRead


class CaseVictimListResponse(CaseScopedList[VictimRead]):
    pass

class VictimListResponse(ListResponse[VictimRead]):
    pass


class TrialRead(SchemaModel):
    case_id: int = Field(..., gt=0)
    open_date: date
    trial_number: int = Field(..., gt=0)
    hearing_date: date | None = Field(
        default=None, description="Maps to trial.hearing."
    )
    judge_id: int | None = Field(default=None, gt=0)
    court_level: str | None = Field(default=None, max_length=50)

    @computed_field(description="API alias for trial_number.")
    @property
    def trial_id(self) -> int:
        return self.trial_number


class CaseTrialListResponse(SchemaModel):
    case_id: int = Field(..., gt=0)
    items: list[TrialRead] = Field(default_factory=list)


class TrialCreateRequest(SchemaModel):
    judge_id: int | None = Field(default=None, gt=0)
    hearing_date: date | None = None
    court_level: str | None = Field(default=None, max_length=50)


class TrialCreateResponse(SchemaModel):
    trial_id: int = Field(..., gt=0)
    trial: TrialRead


class TrialHearingCreateResponse(TrialCreateResponse):
    pass


class TrialHearingCreateRequest(SchemaModel):
    hearing_date: date | None = None
    outcome: str | None = Field(
        default=None, max_length=50, description="Stored in court_level."
    )


class TrialPunishmentCreateRequest(SchemaModel):
    person_ids: list[PositiveInt] = Field(..., min_length=1)
    fine: int | None = Field(default=None, ge=0)
    jail_start: date | None = None
    jail_end: date | None = None
    death_penalty: str | None = Field(default=None, pattern="^[YN]$")

    @model_validator(mode="after")
    def validate_jail_range(self) -> TrialPunishmentCreateRequest:
        if self.jail_start and self.jail_end and self.jail_start > self.jail_end:
            raise ValueError("jail_start cannot be later than jail_end.")
        return self


class PunishmentRead(SchemaModel):
    criminal_person_id: int = Field(
        ..., gt=0, description="Maps to punishment.c_personid."
    )
    case_id: int = Field(..., gt=0)
    open_date: date
    fine: int | None = Field(default=None, ge=0)
    jail_start_date: date | None = None
    jail_end_date: date | None = None
    death_penalty: str | None = Field(default=None, pattern="^[YN]$")
    punishment_type: str | None = Field(default=None, max_length=50)


class TrialPunishmentCreateResponse(SchemaModel):
    trial_id: int = Field(..., gt=0)
    punishments: list[PunishmentRead] = Field(default_factory=list)


class TrialDetailResponse(SchemaModel):
    trial: TrialRead
    punishments: list[PunishmentRead] = Field(default_factory=list)


class CaseDetailResponse(SchemaModel):
    case: CaseRead
    included: list[CaseInclude] = Field(default_factory=list)
    evidence: list[EvidenceRead] = Field(default_factory=list)
    witnesses: list[WitnessRead] = Field(default_factory=list)
    suspects: list[SuspectRead] = Field(default_factory=list)
    victims: list[VictimRead] = Field(default_factory=list)
    trials: list[TrialRead] = Field(default_factory=list)
    testimonies: list[TestimonyRead] = Field(default_factory=list)


class CrimeHotspotQuery(DateRangeQuery):
    city: str | None = Field(default=None, max_length=100)


class CrimeHotspotItem(SchemaModel):
    city: str = Field(..., max_length=100)
    case_count: int = Field(..., ge=0)


class CrimeHotspotResponse(SchemaModel):
    items: list[CrimeHotspotItem] = Field(default_factory=list)
