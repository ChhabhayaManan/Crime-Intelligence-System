"""
Functions for evidence CRUD operations and S3 file handling in the Crime Intelligence System.
- ev_read: Converts an Evidence row to an EvidenceRead for a given case.
- _primary_case: Returns an evidence row's earliest case link, deterministically.
- _fetch_evidence: Fetches an Evidence row with its case links eager-loaded.
- add_case_evidence: Creates evidence and links it to a case.
- list_case_evidence: Lists all evidence collected for a case.
- get_evidence: Fetches one evidence record with its case context.
- upload_evidence_file: Uploads a file to the S3 evidence bucket and returns its key.
- attach_evidence_file: Stores the uploaded file's key, content type and size on the evidence row.
- update_evidence: Applies partial updates to an evidence record.
"""
from __future__ import annotations

import os
from datetime import date
from uuid import uuid4

from sqlalchemy.orm import Session, joinedload, selectinload

from App.db.models import CollectedFor, Evidence
from App.schema.case import (
    CaseEvidenceCreateRequest,
    CaseEvidenceCreateResponse,
    CaseEvidenceListResponse,
    CaseEvidenceUpdateRequest,
    EvidenceRead,
)
from App.CRUD.common import fetch_case, not_found


def ev_read(ev: Evidence, case_id: int, open_date: date) -> EvidenceRead:
    return EvidenceRead(
        evidence_id=ev.evidence_id,
        case_id=case_id,
        open_date=open_date,
        description=ev.description,
        collection_date=ev.collection_date,
        location_id=ev.location_id,
        file_key=ev.file_key,
        file_content_type=ev.file_content_type,
        file_size=ev.file_size,
    )


def _primary_case(ev: Evidence) -> CollectedFor:
    links = sorted(
        ev.collected_for_entries, key=lambda cf: (cf.open_date, cf.case_id)
    )
    if not links:
        raise ValueError(f"Evidence {ev.evidence_id} has no associated case.")
    return links[0]


def _fetch_evidence(db: Session, evidence_id: int) -> Evidence:
    ev = (
        db.query(Evidence)
        .options(selectinload(Evidence.collected_for_entries))
        .filter(Evidence.evidence_id == evidence_id)
        .first()
    )
    if ev is None:
        not_found("Evidence", evidence_id)
    return ev


def add_case_evidence(
    db: Session,
    case_id: int,
    payload: CaseEvidenceCreateRequest,
    open_date: date | None = None,
) -> CaseEvidenceCreateResponse:
    case = fetch_case(db, case_id, open_date)

    ev = Evidence(
        description=payload.description,
        collection_date=payload.collected_at,
        location_id=payload.location_id,
    )
    db.add(ev)
    db.flush()

    db.add(
        CollectedFor(
            evidence_id=ev.evidence_id,
            case_id=case.case_id,
            open_date=case.open_date,
        )
    )
    db.flush()

    return CaseEvidenceCreateResponse(
        evidence_id=ev.evidence_id,
        evidence=ev_read(ev, case.case_id, case.open_date),
    )


def list_case_evidence(
    db: Session,
    case_id: int,
    open_date: date | None = None,
) -> CaseEvidenceListResponse:
    case = fetch_case(db, case_id, open_date)

    links = (
        db.query(CollectedFor)
        .options(joinedload(CollectedFor.evidence))
        .filter(
            CollectedFor.case_id == case.case_id,
            CollectedFor.open_date == case.open_date,
        )
        .all()
    )

    return CaseEvidenceListResponse(
        case_id=case.case_id,
        open_date=case.open_date,
        items=[ev_read(cf.evidence, cf.case_id, cf.open_date) for cf in links],
    )


def get_evidence(db: Session, evidence_id: int) -> EvidenceRead:
    ev = _fetch_evidence(db, evidence_id)
    cf = _primary_case(ev)
    return ev_read(ev, cf.case_id, cf.open_date)


def upload_evidence_file(
    content: bytes,
    evidence_id: int,
    content_type: str,
    ext: str,
) -> str:
    import boto3

    bucket = os.environ["S3_EVIDENCE_BUCKET"]
    key = f"evidence/{evidence_id}/{uuid4().hex}.{ext}"

    boto3.client("s3").put_object(
        Bucket=bucket,
        Key=key,
        Body=content,
        ContentType=content_type,
        ServerSideEncryption="AES256",
    )
    return key


def attach_evidence_file(
    db: Session,
    evidence_id: int,
    key: str,
    content_type: str,
    size: int,
) -> EvidenceRead:
    ev = _fetch_evidence(db, evidence_id)

    ev.file_key = key
    ev.file_content_type = content_type
    ev.file_size = size
    db.flush()

    cf = _primary_case(ev)
    return ev_read(ev, cf.case_id, cf.open_date)


def update_evidence(
    db: Session,
    evidence_id: int,
    payload: CaseEvidenceUpdateRequest,
) -> EvidenceRead:
    ev = _fetch_evidence(db, evidence_id)
    given = payload.model_dump(exclude_unset=True)

    if "description" in given:
        ev.description = payload.description
    if "location_id" in given:
        ev.location_id = payload.location_id
    if "collected_at" in given:
        ev.collection_date = payload.collected_at

    db.flush()

    cf = _primary_case(ev)
    return ev_read(ev, cf.case_id, cf.open_date)
