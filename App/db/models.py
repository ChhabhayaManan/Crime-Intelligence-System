from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    func,
    inspect,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .session import Base

_CASCADE = {"cascade": "all, delete", "passive_deletes": True}

# Mixin class for providing a string representation of ORM objects
class ReprMixin:
    def __repr__(self) -> str:
        mapper = inspect(type(self))
        keys = [mapper.get_property_by_column(c).key for c in mapper.primary_key]
        fields = ", ".join(f"{k}={getattr(self, k)!r}" for k in keys)
        return f"{type(self).__name__}({fields})"

# address ORM table to store address information
class Address(ReprMixin, Base):
    __tablename__ = "address"

    address_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    street_address: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    pin_code: Mapped[Optional[str]] = mapped_column("postal_code", String(20))
    country: Mapped[Optional[str]] = mapped_column(String(100))

    residents: Mapped[list["Person"]] = relationship(back_populates="address")
    case_locations: Mapped[list["CaseDetail"]] = relationship(
        back_populates="crime_location_address",
        foreign_keys="CaseDetail.crime_location",
    )
    evidence_locations: Mapped[list["Evidence"]] = relationship(
        back_populates="location",
        foreign_keys="Evidence.location_id",
    )

# person ORM table to store person information
class Person(ReprMixin, Base):
    __tablename__ = "person"

    person_id: Mapped[int] = mapped_column("personid", Integer, primary_key=True)
    gender: Mapped[Optional[str]] = mapped_column(String(1))
    birth_date: Mapped[Optional[date]] = mapped_column(Date)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    middle_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    address_id: Mapped[Optional[int]] = mapped_column(ForeignKey("address.address_id"))
    occupation: Mapped[Optional[str]] = mapped_column(String(100))
    contact_number: Mapped[Optional[str]] = mapped_column(String(15))

    address: Mapped[Optional["Address"]] = relationship(back_populates="residents")
    reported_cases: Mapped[list["CaseDetail"]] = relationship(
        back_populates="reporting_person",
        foreign_keys="CaseDetail.person_id",
    )
    police_profile: Mapped[Optional["PoliceOfficer"]] = relationship(
        back_populates="person", uselist=False, lazy="selectin", **_CASCADE
    )
    criminal_profile: Mapped[Optional["Criminal"]] = relationship(
        back_populates="person", uselist=False, lazy="selectin", **_CASCADE
    )
    suspect_profile: Mapped[Optional["Suspect"]] = relationship(
        back_populates="person", uselist=False, lazy="selectin", **_CASCADE
    )
    victim_profile: Mapped[Optional["Victim"]] = relationship(
        back_populates="person", uselist=False, lazy="selectin", **_CASCADE
    )
    witness_profile: Mapped[Optional["Witness"]] = relationship(
        back_populates="person", uselist=False, lazy="selectin", **_CASCADE
    )

# case detail ORM table to store case information
class CaseDetail(ReprMixin, Base):
    __tablename__ = "case_details"

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)
    crime_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    complaint_detail: Mapped[Optional[str]] = mapped_column(String(255))
    crime_type: Mapped[Optional[str]] = mapped_column(String(50))
    crime_location: Mapped[Optional[int]] = mapped_column(
        ForeignKey("address.address_id")
    )
    case_status: Mapped[Optional[str]] = mapped_column(String(10))
    person_id: Mapped[Optional[int]] = mapped_column(
        "personid",
        ForeignKey("person.personid"),
    )

    reporting_person: Mapped[Optional["Person"]] = relationship(
        back_populates="reported_cases",
        foreign_keys=[person_id],
    )
    crime_location_address: Mapped[Optional["Address"]] = relationship(
        back_populates="case_locations",
        foreign_keys=[crime_location],
    )
    trials: Mapped[list["Trial"]] = relationship(
        back_populates="case_detail", **_CASCADE
    )
    collected_for_entries: Mapped[list["CollectedFor"]] = relationship(
        back_populates="case_detail", **_CASCADE
    )
    testifies_in_entries: Mapped[list["TestifiesIn"]] = relationship(
        back_populates="case_detail", **_CASCADE
    )
    assigned_to_entries: Mapped[list["AssignedTo"]] = relationship(
        back_populates="case_detail", **_CASCADE
    )
    affected_by_entries: Mapped[list["AffectedBy"]] = relationship(
        back_populates="case_detail", **_CASCADE
    )
    punishment_entries: Mapped[list["Punishment"]] = relationship(
        back_populates="case_detail", **_CASCADE
    )
    involved_in_entries: Mapped[list["InvolvedIn"]] = relationship(
        back_populates="case_detail", **_CASCADE
    )

# trial ORM table to store trial information
class Trial(ReprMixin, Base):
    __tablename__ = "trial"
    __table_args__ = (
        ForeignKeyConstraint(
            ["case_id", "open_date"],
            ["case_details.case_id", "case_details.open_date"],
            ondelete="CASCADE",
        ),
    )

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)
    trial_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    hearing: Mapped[Optional[date]] = mapped_column(Date)
    judge_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("person.personid", ondelete="SET NULL")
    )
    court_level: Mapped[Optional[str]] = mapped_column(String(50))

    case_detail: Mapped["CaseDetail"] = relationship(back_populates="trials")
    judge: Mapped[Optional["Person"]] = relationship(foreign_keys=[judge_id])

# police officer ORM table to store police officer information
class PoliceOfficer(ReprMixin, Base):
    __tablename__ = "police_officer"

    officer_person_id: Mapped[int] = mapped_column(
        "p_personid",
        ForeignKey("person.personid", ondelete="CASCADE"),
        primary_key=True,
    )
    rank: Mapped[Optional[str]] = mapped_column(String(50))
    department: Mapped[Optional[str]] = mapped_column(String(100))

    person: Mapped["Person"] = relationship(back_populates="police_profile")
    assignments: Mapped[list["AssignedTo"]] = relationship(
        back_populates="officer", **_CASCADE
    )

# criminal ORM table to store criminal information
class Criminal(ReprMixin, Base):
    __tablename__ = "criminal"

    criminal_person_id: Mapped[int] = mapped_column(
        "c_personid",
        ForeignKey("person.personid", ondelete="CASCADE"),
        primary_key=True,
    )
    family_contact: Mapped[Optional[str]] = mapped_column(
        "c_family_contact", String(15)
    )

    person: Mapped["Person"] = relationship(back_populates="criminal_profile")
    punishments: Mapped[list["Punishment"]] = relationship(
        back_populates="criminal", **_CASCADE
    )

# suspect ORM table to store suspect information
class Suspect(ReprMixin, Base):
    __tablename__ = "suspect"

    suspect_person_id: Mapped[int] = mapped_column(
        "s_personid",
        ForeignKey("person.personid", ondelete="CASCADE"),
        primary_key=True,
    )
    physical_description: Mapped[Optional[str]] = mapped_column(String(255))
    family_contact: Mapped[Optional[str]] = mapped_column(String(15))
    arrest_status: Mapped[Optional[str]] = mapped_column(String(50))

    person: Mapped["Person"] = relationship(back_populates="suspect_profile")
    involvements: Mapped[list["InvolvedIn"]] = relationship(
        back_populates="suspect", **_CASCADE
    )
    linked_evidence: Mapped[list["LinkedTo"]] = relationship(
        back_populates="suspect", **_CASCADE
    )
    pointed_to_entries: Mapped[list["PointedTo"]] = relationship(
        back_populates="suspect", **_CASCADE
    )

# victim ORM table to store victim information
class Victim(ReprMixin, Base):
    __tablename__ = "victim"

    victim_person_id: Mapped[int] = mapped_column(
        "v_personid",
        ForeignKey("person.personid", ondelete="CASCADE"),
        primary_key=True,
    )
    harm_details: Mapped[Optional[str]] = mapped_column(String(255))
    family_contact: Mapped[Optional[str]] = mapped_column(String(15))

    person: Mapped["Person"] = relationship(back_populates="victim_profile")
    affected_cases: Mapped[list["AffectedBy"]] = relationship(
        back_populates="victim", **_CASCADE
    )

# witness ORM table to store witness information
class Witness(ReprMixin, Base):
    __tablename__ = "witness"

    witness_person_id: Mapped[int] = mapped_column(
        "w_personid",
        ForeignKey("person.personid", ondelete="CASCADE"),
        primary_key=True,
    )
    family_contact: Mapped[Optional[str]] = mapped_column(String(15))
    testimony: Mapped[Optional[str]] = mapped_column(String(255))

    person: Mapped["Person"] = relationship(back_populates="witness_profile")
    testifies_in_cases: Mapped[list["TestifiesIn"]] = relationship(
        back_populates="witness", **_CASCADE
    )

# evidence ORM table to store evidence information
class Evidence(ReprMixin, Base):
    __tablename__ = "evidence"

    evidence_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    collection_date: Mapped[Optional[date]] = mapped_column(Date)
    location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("address.address_id", ondelete="SET NULL")
    )
    file_key: Mapped[Optional[str]] = mapped_column(String(1024))
    file_content_type: Mapped[Optional[str]] = mapped_column(String(255))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)

    location: Mapped[Optional["Address"]] = relationship(
        back_populates="evidence_locations",
        foreign_keys=[location_id],
    )
    collected_for_entries: Mapped[list["CollectedFor"]] = relationship(
        back_populates="evidence", **_CASCADE
    )

# association table for the many-to-many relationship between Evidence and CaseDetail
class CollectedFor(ReprMixin, Base):
    __tablename__ = "collected_for"
    __table_args__ = (
        ForeignKeyConstraint(
            ["evidence_id"], ["evidence.evidence_id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["case_id", "open_date"],
            ["case_details.case_id", "case_details.open_date"],
            ondelete="CASCADE",
        ),
    )

    evidence_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)

    evidence: Mapped["Evidence"] = relationship(back_populates="collected_for_entries")
    case_detail: Mapped["CaseDetail"] = relationship(
        back_populates="collected_for_entries"
    )
    linked_to_entries: Mapped[list["LinkedTo"]] = relationship(
        back_populates="collected_for", **_CASCADE
    )

# association table for the many-to-many relationship between Witness and CaseDetail
class TestifiesIn(ReprMixin, Base):
    __tablename__ = "testifies_in"
    __table_args__ = (
        ForeignKeyConstraint(
            ["case_id", "open_date"],
            ["case_details.case_id", "case_details.open_date"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["w_personid"], ["witness.w_personid"], ondelete="CASCADE"
        ),
    )

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)
    witness_person_id: Mapped[int] = mapped_column(
        "w_personid", Integer, primary_key=True
    )
    testimony: Mapped[Optional[str]] = mapped_column(String(255))

    case_detail: Mapped["CaseDetail"] = relationship(
        back_populates="testifies_in_entries"
    )
    witness: Mapped["Witness"] = relationship(back_populates="testifies_in_cases")
    pointed_to_entries: Mapped[list["PointedTo"]] = relationship(
        back_populates="testimony", **_CASCADE
    )

# association table for the many-to-many relationship between PoliceOfficer and CaseDetail
class AssignedTo(ReprMixin, Base):
    __tablename__ = "assigned_to"
    __table_args__ = (
        ForeignKeyConstraint(
            ["p_personid"], ["police_officer.p_personid"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["case_id", "open_date"],
            ["case_details.case_id", "case_details.open_date"],
            ondelete="CASCADE",
        ),
    )

    officer_person_id: Mapped[int] = mapped_column(
        "p_personid", Integer, primary_key=True
    )
    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)

    officer: Mapped["PoliceOfficer"] = relationship(back_populates="assignments")
    case_detail: Mapped["CaseDetail"] = relationship(
        back_populates="assigned_to_entries"
    )

# association table for the relationship between Victim and CaseDetail
class AffectedBy(ReprMixin, Base):
    __tablename__ = "affected_by"
    __table_args__ = (
        ForeignKeyConstraint(
            ["v_personid"], ["victim.v_personid"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["case_id", "open_date"],
            ["case_details.case_id", "case_details.open_date"],
            ondelete="CASCADE",
        ),
    )

    victim_person_id: Mapped[int] = mapped_column(
        "v_personid", Integer, primary_key=True
    )
    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)

    victim: Mapped["Victim"] = relationship(back_populates="affected_cases")
    case_detail: Mapped["CaseDetail"] = relationship(
        back_populates="affected_by_entries"
    )

# association table for the relationship between Criminal and CaseDetail
class Punishment(ReprMixin, Base):
    __tablename__ = "punishment"
    __table_args__ = (
        ForeignKeyConstraint(
            ["c_personid"], ["criminal.c_personid"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["case_id", "open_date"],
            ["case_details.case_id", "case_details.open_date"],
            ondelete="CASCADE",
        ),
    )

    criminal_person_id: Mapped[int] = mapped_column(
        "c_personid", Integer, primary_key=True
    )
    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)
    fine: Mapped[Optional[int]] = mapped_column(Integer)
    jail_start_date: Mapped[Optional[date]] = mapped_column(Date)
    jail_end_date: Mapped[Optional[date]] = mapped_column(Date)
    death_penalty: Mapped[Optional[str]] = mapped_column(String(1))

    criminal: Mapped["Criminal"] = relationship(back_populates="punishments")
    case_detail: Mapped["CaseDetail"] = relationship(
        back_populates="punishment_entries"
    )

# association table for the relationship between Suspect and CaseDetail
class InvolvedIn(ReprMixin, Base):
    __tablename__ = "involved_in"
    __table_args__ = (
        ForeignKeyConstraint(
            ["case_id", "open_date"],
            ["case_details.case_id", "case_details.open_date"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["s_personid"], ["suspect.s_personid"], ondelete="CASCADE"
        ),
    )

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)
    suspect_person_id: Mapped[int] = mapped_column(
        "s_personid", Integer, primary_key=True
    )

    case_detail: Mapped["CaseDetail"] = relationship(
        back_populates="involved_in_entries"
    )
    suspect: Mapped["Suspect"] = relationship(back_populates="involvements")

# association table for the relationship between Suspect and Evidence
class LinkedTo(ReprMixin, Base):
    __tablename__ = "linked_to"
    __table_args__ = (
        ForeignKeyConstraint(
            ["s_personid"], ["suspect.s_personid"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["case_id", "open_date", "evidence_id"],
            [
                "collected_for.case_id",
                "collected_for.open_date",
                "collected_for.evidence_id",
            ],
            ondelete="CASCADE",
        ),
    )

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)
    suspect_person_id: Mapped[int] = mapped_column(
        "s_personid", Integer, primary_key=True
    )
    evidence_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    suspect: Mapped["Suspect"] = relationship(back_populates="linked_evidence")
    collected_for: Mapped["CollectedFor"] = relationship(
        back_populates="linked_to_entries"
    )

# association table for the relationship between Suspect and Witness
class PointedTo(ReprMixin, Base):
    __tablename__ = "pointed_to"
    __table_args__ = (
        ForeignKeyConstraint(
            ["s_personid"], ["suspect.s_personid"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["case_id", "open_date", "w_personid"],
            [
                "testifies_in.case_id",
                "testifies_in.open_date",
                "testifies_in.w_personid",
            ],
            ondelete="CASCADE",
        ),
    )

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)
    suspect_person_id: Mapped[int] = mapped_column(
        "s_personid", Integer, primary_key=True
    )
    witness_person_id: Mapped[int] = mapped_column(
        "w_personid", Integer, primary_key=True
    )

    suspect: Mapped["Suspect"] = relationship(back_populates="pointed_to_entries")
    testimony: Mapped["TestifiesIn"] = relationship(
        back_populates="pointed_to_entries"
    )

# app user ORM table to store application user information
class AppUser(ReprMixin, Base):
    __tablename__ = "app_user"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    mobile_number: Mapped[Optional[str]] = mapped_column(String(15))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


__all__ = [
    "Base",
    "Address",
    "Person",
    "CaseDetail",
    "Trial",
    "PoliceOfficer",
    "Criminal",
    "Suspect",
    "Victim",
    "Witness",
    "Evidence",
    "CollectedFor",
    "TestifiesIn",
    "AssignedTo",
    "AffectedBy",
    "Punishment",
    "InvolvedIn",
    "LinkedTo",
    "PointedTo",
    "AppUser",
]
