""" Object-Relational Mapping (ORM) models for the Crime Tracking and Analysis Database. """

from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Boolean, Date, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from .session import Base
from sqlalchemy import inspect


class Address(Base):
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

    def __repr__(self) -> str:
        return (
            f"Address(address_id={self.address_id!r}, city={self.city!r}, "
            f"country={self.country!r})"
        )


class Person(Base):
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
        back_populates="person",
        uselist=False,
    )
    criminal_profile: Mapped[Optional["Criminal"]] = relationship(
        back_populates="person",
        uselist=False,
    )
    suspect_profile: Mapped[Optional["Suspect"]] = relationship(
        back_populates="person",
        uselist=False,
    )
    victim_profile: Mapped[Optional["Victim"]] = relationship(
        back_populates="person",
        uselist=False,
    )
    witness_profile: Mapped[Optional["Witness"]] = relationship(
        back_populates="person",
        uselist=False,
    )

    def __repr__(self) -> str:
        return (
            f"Person(person_id={self.person_id!r}, first_name={self.first_name!r}, "
            f"last_name={self.last_name!r})"
        )


class CaseDetail(Base):
    __tablename__ = "case_details"

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)
    crime_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    complaint_detail: Mapped[Optional[str]] = mapped_column(String(255))
    crime_type: Mapped[Optional[str]] = mapped_column(String(50))
    crime_location: Mapped[Optional[int]] = mapped_column(ForeignKey("address.address_id"))
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
    trials: Mapped[list["Trial"]] = relationship(back_populates="case_detail")
    collected_for_entries: Mapped[list["CollectedFor"]] = relationship(
        back_populates="case_detail"
    )
    testifies_in_entries: Mapped[list["TestifiesIn"]] = relationship(
        back_populates="case_detail"
    )
    assigned_to_entries: Mapped[list["AssignedTo"]] = relationship(
        back_populates="case_detail"
    )
    affected_by_entries: Mapped[list["AffectedBy"]] = relationship(
        back_populates="case_detail"
    )
    punishment_entries: Mapped[list["Punishment"]] = relationship(
        back_populates="case_detail"
    )
    involved_in_entries: Mapped[list["InvolvedIn"]] = relationship(
        back_populates="case_detail"
    )

    def __repr__(self) -> str:
        return (
            f"CaseDetail(case_id={self.case_id!r}, open_date={self.open_date!r}, "
            f"crime_type={self.crime_type!r})"
        )


class Trial(Base):
    __tablename__ = "trial"
    __table_args__ = (
        ForeignKeyConstraint(
            ["case_id", "open_date"],
            ["case_details.case_id", "case_details.open_date"],
        ),
    )

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)
    trial_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    hearing: Mapped[Optional[date]] = mapped_column(Date)
    judge_id: Mapped[Optional[int]] = mapped_column(Integer)
    court_level: Mapped[Optional[str]] = mapped_column(String(50))

    case_detail: Mapped["CaseDetail"] = relationship(back_populates="trials")

    def __repr__(self) -> str:
        return (
            f"Trial(case_id={self.case_id!r}, open_date={self.open_date!r}, "
            f"trial_number={self.trial_number!r})"
        )


class PoliceOfficer(Base):
    __tablename__ = "police_officer"

    officer_person_id: Mapped[int] = mapped_column(
        "p_personid",
        ForeignKey("person.personid"),
        primary_key=True,
    )
    rank: Mapped[Optional[str]] = mapped_column(String(50))
    department: Mapped[Optional[str]] = mapped_column(String(100))

    person: Mapped["Person"] = relationship(back_populates="police_profile")
    assignments: Mapped[list["AssignedTo"]] = relationship(back_populates="officer")

    def __repr__(self) -> str:
        return (
            f"PoliceOfficer(officer_person_id={self.officer_person_id!r}, "
            f"rank={self.rank!r})"
        )


class Criminal(Base):
    __tablename__ = "criminal"

    criminal_person_id: Mapped[int] = mapped_column(
        "c_personid",
        ForeignKey("person.personid"),
        primary_key=True,
    )
    
    family_contact: Mapped[Optional[str]] = mapped_column("c_family_contact", String(15))

    person: Mapped["Person"] = relationship(back_populates="criminal_profile")
    punishments: Mapped[list["Punishment"]] = relationship(back_populates="criminal")

    def __repr__(self) -> str:
        return (
            f"Criminal(criminal_person_id={self.criminal_person_id!r}, "
            f"family_contact={self.family_contact!r})"
        )


class Suspect(Base):
    __tablename__ = "suspect"

    suspect_person_id: Mapped[int] = mapped_column(
        "s_personid",
        ForeignKey("person.personid"),
        primary_key=True,
    )
    physical_description: Mapped[Optional[str]] = mapped_column(String(255))
    family_contact: Mapped[Optional[str]] = mapped_column(String(15))
    arrest_status: Mapped[Optional[str]] = mapped_column(String(50))

    person: Mapped["Person"] = relationship(back_populates="suspect_profile")
    involvements: Mapped[list["InvolvedIn"]] = relationship(back_populates="suspect")
    linked_evidence: Mapped[list["LinkedTo"]] = relationship(back_populates="suspect")
    pointed_to_entries: Mapped[list["PointedTo"]] = relationship(back_populates="suspect")

    def __repr__(self) -> str:
        return (
            f"Suspect(suspect_person_id={self.suspect_person_id!r}, "
            f"arrest_status={self.arrest_status!r})"
        )


class Victim(Base):
    __tablename__ = "victim"

    victim_person_id: Mapped[int] = mapped_column(
        "v_personid",
        ForeignKey("person.personid"),
        primary_key=True,
    )
    harm_details: Mapped[Optional[str]] = mapped_column(String(255))
    family_contact: Mapped[Optional[str]] = mapped_column(String(15))

    person: Mapped["Person"] = relationship(back_populates="victim_profile")
    affected_cases: Mapped[list["AffectedBy"]] = relationship(back_populates="victim")

    def __repr__(self) -> str:
        return (
            f"Victim(victim_person_id={self.victim_person_id!r}, "
            f"harm_details={self.harm_details!r})"
        )


class Witness(Base):
    __tablename__ = "witness"

    witness_person_id: Mapped[int] = mapped_column(
        "w_personid",
        ForeignKey("person.personid"),
        primary_key=True,
    )
    family_contact: Mapped[Optional[str]] = mapped_column(String(15))
    testimony: Mapped[Optional[str]] = mapped_column(String(255))

    person: Mapped["Person"] = relationship(back_populates="witness_profile")
    testifies_in_cases: Mapped[list["TestifiesIn"]] = relationship(back_populates="witness")

    def __repr__(self) -> str:
        return (
            f"Witness(witness_person_id={self.witness_person_id!r}, "
            f"family_contact={self.family_contact!r})"
        )


class Evidence(Base):
    __tablename__ = "evidence"

    evidence_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    collection_date: Mapped[Optional[date]] = mapped_column(Date)

    location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("address.address_id")
    )

    location: Mapped[Optional["Address"]] = relationship()

    collected_for_entries: Mapped[list["CollectedFor"]] = relationship(
        back_populates="evidence"
    )

    def __repr__(self) -> str:
        return (
            f"Evidence(evidence_id={self.evidence_id!r}, "
            f"collection_date={self.collection_date!r}, "
            f"location_id={self.location_id!r})"
        )


class CollectedFor(Base):
    __tablename__ = "collected_for"
    __table_args__ = (
        ForeignKeyConstraint(["evidence_id"], ["evidence.evidence_id"]),
        ForeignKeyConstraint(
            ["case_id", "open_date"],
            ["case_details.case_id", "case_details.open_date"],
        ),
    )

    evidence_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)

    evidence: Mapped["Evidence"] = relationship(back_populates="collected_for_entries")
    case_detail: Mapped["CaseDetail"] = relationship(back_populates="collected_for_entries")
    linked_to_entries: Mapped[list["LinkedTo"]] = relationship(back_populates="collected_for")

    def __repr__(self) -> str:
        return (
            f"CollectedFor(evidence_id={self.evidence_id!r}, case_id={self.case_id!r}, "
            f"open_date={self.open_date!r})"
        )


class TestifiesIn(Base):
    __tablename__ = "testifies_in"
    __table_args__ = (
        ForeignKeyConstraint(
            ["case_id", "open_date"],
            ["case_details.case_id", "case_details.open_date"],
        ),
        ForeignKeyConstraint(["w_personid"], ["witness.w_personid"]),
    )

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)
    witness_person_id: Mapped[int] = mapped_column("w_personid", Integer, primary_key=True)

    case_detail: Mapped["CaseDetail"] = relationship(back_populates="testifies_in_entries")
    witness: Mapped["Witness"] = relationship(back_populates="testifies_in_cases")
    pointed_to_entries: Mapped[list["PointedTo"]] = relationship(back_populates="testimony")

    def __repr__(self) -> str:
        return (
            f"TestifiesIn(case_id={self.case_id!r}, open_date={self.open_date!r}, "
            f"witness_person_id={self.witness_person_id!r})"
        )


class AssignedTo(Base):
    __tablename__ = "assigned_to"
    __table_args__ = (
        ForeignKeyConstraint(["p_personid"], ["police_officer.p_personid"]),
        ForeignKeyConstraint(
            ["case_id", "open_date"],
            ["case_details.case_id", "case_details.open_date"],
        ),
    )

    officer_person_id: Mapped[int] = mapped_column("p_personid", Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)

    officer: Mapped["PoliceOfficer"] = relationship(back_populates="assignments")
    case_detail: Mapped["CaseDetail"] = relationship(back_populates="assigned_to_entries")

    def __repr__(self) -> str:
        return (
            f"AssignedTo(officer_person_id={self.officer_person_id!r}, "
            f"case_id={self.case_id!r}, open_date={self.open_date!r})"
        )


class AffectedBy(Base):
    __tablename__ = "affected_by"
    __table_args__ = (
        ForeignKeyConstraint(["v_personid"], ["victim.v_personid"]),
        ForeignKeyConstraint(
            ["case_id", "open_date"],
            ["case_details.case_id", "case_details.open_date"],
        ),
    )

    victim_person_id: Mapped[int] = mapped_column("v_personid", Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)

    victim: Mapped["Victim"] = relationship(back_populates="affected_cases")
    case_detail: Mapped["CaseDetail"] = relationship(back_populates="affected_by_entries")

    def __repr__(self) -> str:
        return (
            f"AffectedBy(victim_person_id={self.victim_person_id!r}, "
            f"case_id={self.case_id!r}, open_date={self.open_date!r})"
        )


class Punishment(Base):
    __tablename__ = "punishment"
    __table_args__ = (
        ForeignKeyConstraint(["c_personid"], ["criminal.c_personid"]),
        ForeignKeyConstraint(
            ["case_id", "open_date"],
            ["case_details.case_id", "case_details.open_date"],
        ),
    )

    criminal_person_id: Mapped[int] = mapped_column("c_personid", Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)
    fine: Mapped[Optional[int]] = mapped_column(Integer)
    jail_start_date: Mapped[Optional[date]] = mapped_column(Date)
    jail_end_date: Mapped[Optional[date]] = mapped_column(Date)
    death_penalty: Mapped[Optional[str]] = mapped_column(String(1))

    criminal: Mapped["Criminal"] = relationship(back_populates="punishments")
    case_detail: Mapped["CaseDetail"] = relationship(back_populates="punishment_entries")

    def __repr__(self) -> str:
        return (
            f"Punishment(criminal_person_id={self.criminal_person_id!r}, "
            f"case_id={self.case_id!r}, open_date={self.open_date!r})"
        )


class InvolvedIn(Base):
    __tablename__ = "involved_in"
    __table_args__ = (
        ForeignKeyConstraint(
            ["case_id", "open_date"],
            ["case_details.case_id", "case_details.open_date"],
        ),
        ForeignKeyConstraint(["s_personid"], ["suspect.s_personid"]),
    )

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)
    suspect_person_id: Mapped[int] = mapped_column("s_personid", Integer, primary_key=True)

    case_detail: Mapped["CaseDetail"] = relationship(back_populates="involved_in_entries")
    suspect: Mapped["Suspect"] = relationship(back_populates="involvements")

    def __repr__(self) -> str:
        return (
            f"InvolvedIn(case_id={self.case_id!r}, open_date={self.open_date!r}, "
            f"suspect_person_id={self.suspect_person_id!r})"
        )


class LinkedTo(Base):
    __tablename__ = "linked_to"
    __table_args__ = (
        ForeignKeyConstraint(["s_personid"], ["suspect.s_personid"]),
        ForeignKeyConstraint(
            ["case_id", "open_date", "evidence_id"],
            ["collected_for.case_id", "collected_for.open_date", "collected_for.evidence_id"],
        ),
    )

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)
    suspect_person_id: Mapped[int] = mapped_column("s_personid", Integer, primary_key=True)
    evidence_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    suspect: Mapped["Suspect"] = relationship(back_populates="linked_evidence")
    collected_for: Mapped["CollectedFor"] = relationship(back_populates="linked_to_entries")

    def __repr__(self) -> str:
        return (
            f"LinkedTo(case_id={self.case_id!r}, open_date={self.open_date!r}, "
            f"suspect_person_id={self.suspect_person_id!r}, evidence_id={self.evidence_id!r})"
        )


class PointedTo(Base):
    __tablename__ = "pointed_to"
    __table_args__ = (
        ForeignKeyConstraint(["s_personid"], ["suspect.s_personid"]),
        ForeignKeyConstraint(
            ["case_id", "open_date", "w_personid"],
            ["testifies_in.case_id", "testifies_in.open_date", "testifies_in.w_personid"],
        ),
    )

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_date: Mapped[date] = mapped_column(Date, primary_key=True)
    suspect_person_id: Mapped[int] = mapped_column("s_personid", Integer, primary_key=True)
    witness_person_id: Mapped[int] = mapped_column("w_personid", Integer, primary_key=True)

    suspect: Mapped["Suspect"] = relationship(back_populates="pointed_to_entries")
    testimony: Mapped["TestifiesIn"] = relationship(back_populates="pointed_to_entries")

    def __repr__(self) -> str:
        return (
            f"PointedTo(case_id={self.case_id!r}, open_date={self.open_date!r}, "
            f"suspect_person_id={self.suspect_person_id!r}, "
            f"witness_person_id={self.witness_person_id!r})"
        )

class AppUser(Base):
    __tablename__ = "app_user"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)  # bcrypt hash
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    mobile_number: Mapped[Optional[str]] = mapped_column(String(15))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"AppUser(user_id={self.user_id!r}, username={self.username!r}, role={self.role!r})"


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

