"""
evidence.py
-----------
CRUD operations for Evidence entities.

Functions
---------
  add_case_evidence   – POST /cases/{case_id}/evidence
  list_case_evidence  – GET  /cases/{case_id}/evidence
  get_evidence        – GET  /evidence/{evidence_id}
  update_evidence     – PATCH /evidence/{evidence_id}
"""

from __future__ import annotations
import os
from datetime import date
from uuid import uuid4

import boto3
from sqlalchemy.orm import Session
from App.db.models import (
    CollectedFor,
    Evidence,
)
from App.schema.case import (
    CaseEvidenceCreateRequest,
    CaseEvidenceCreateResponse,
    CaseEvidenceListResponse,
    EvidenceRead,
)
from App.CRUD.common import next_id, not_found, fetch_case

# ---------------------------------------------------------------------------
# Internal mapper
# ---------------------------------------------------------------------------

def _ev_read(ev: Evidence, case_id: int, open_date: date) -> EvidenceRead:
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


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def add_case_evidence(
    db: Session,
    case_id: int,
    payload: CaseEvidenceCreateRequest,
    open_date: date | None = None,
) -> CaseEvidenceCreateResponse:
    """Create a new Evidence row and link it to the given case via CollectedFor."""
    case = fetch_case(db, case_id, open_date)

    new_ev_id = next_id(db, Evidence, "evidence_id")
    ev = Evidence(
        evidence_id=new_ev_id,
        description=payload.description,
        collection_date=payload.collected_at,
        location_id=payload.location_id,
    )
    db.add(ev)
    db.flush()

    cf = CollectedFor(
        evidence_id=new_ev_id,
        case_id=case.case_id,
        open_date=case.open_date,
    )
    db.add(cf)
    db.commit()
    db.refresh(ev)

    ev_read = _ev_read(ev, case.case_id, case.open_date)
    return CaseEvidenceCreateResponse(evidence_id=ev.evidence_id, evidence=ev_read)


def list_case_evidence(
    db: Session,
    case_id: int,
    open_date: date | None = None,
) -> CaseEvidenceListResponse:
    """Return all evidence items collected for a given case."""
    case = fetch_case(db, case_id, open_date)

    items = [
        _ev_read(cf.evidence, cf.case_id, cf.open_date)
        for cf in case.collected_for_entries
    ]

    return CaseEvidenceListResponse(
        case_id=case.case_id,
        open_date=case.open_date,
        items=items,
    )


def get_evidence(db: Session, evidence_id: int) -> EvidenceRead:
    """Fetch a single evidence item by ID."""
    ev = db.get(Evidence, evidence_id)
    if ev is None:
        not_found("Evidence", evidence_id)

    cf = ev.collected_for_entries[0] if ev.collected_for_entries else None  # type: ignore[union-attr]
    if cf is None:
        raise ValueError(f"Evidence {evidence_id} has no associated case.")

    return _ev_read(ev, cf.case_id, cf.open_date)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Evidence file storage (S3)
# ---------------------------------------------------------------------------

def upload_evidence_file(
    content: bytes,
    evidence_id: int,
    content_type: str,
    ext: str,
) -> str:
    """Upload an evidence file to the S3 evidence bucket and return its key.

    Credentials are resolved from the ECS task role — none are stored in code.
    """
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
    """Persist file metadata onto an existing evidence row."""
    ev = db.get(Evidence, evidence_id)
    if ev is None:
        not_found("Evidence", evidence_id)

    ev.file_key = key  # type: ignore[union-attr]
    ev.file_content_type = content_type  # type: ignore[union-attr]
    ev.file_size = size  # type: ignore[union-attr]

    db.commit()
    db.refresh(ev)

    cf = ev.collected_for_entries[0] if ev.collected_for_entries else None  # type: ignore[union-attr]
    if cf is None:
        raise ValueError(f"Evidence {evidence_id} has no associated case.")

    return _ev_read(ev, cf.case_id, cf.open_date)  # type: ignore[arg-type]


def update_evidence(
    db: Session,
    evidence_id: int,
    description: str | None = None,
    location_id: int | None = None,
    collected_at: date | None = None,
) -> EvidenceRead:
    """Partially update an evidence record."""
    ev = db.get(Evidence, evidence_id)
    if ev is None:
        not_found("Evidence", evidence_id)

    if description is not None:
        ev.description = description  # type: ignore[union-attr]
    if location_id is not None:
        ev.location_id = location_id  # type: ignore[union-attr]
    if collected_at is not None:
        ev.collection_date = collected_at  # type: ignore[union-attr]

    db.commit()
    db.refresh(ev)

    cf = ev.collected_for_entries[0] if ev.collected_for_entries else None  # type: ignore[union-attr]
    if cf is None:
        raise ValueError(f"Evidence {evidence_id} has no associated case.")

    return _ev_read(ev, cf.case_id, cf.open_date)  # type: ignore[arg-type]
