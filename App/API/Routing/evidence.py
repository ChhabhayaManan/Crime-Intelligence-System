"""
evidence.py
-----------
FastAPI router for Evidence CRUD endpoints (case-scoped).

Endpoints
---------
  POST   /cases/{case_id}/evidence              – add_case_evidence
  GET    /cases/{case_id}/evidence              – list_case_evidence
  GET    /evidence/{evidence_id}                – get_evidence
  PATCH  /evidence/{evidence_id}                – update_evidence
"""

from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from App.API.deps import get_db
from App.db.models import Evidence
from App.schema.case import (
    CaseEvidenceCreateRequest,
    CaseEvidenceCreateResponse,
    CaseEvidenceListResponse,
    EvidenceRead,
)
from App.CRUD.evidence import (
    add_case_evidence,
    attach_evidence_file,
    get_evidence,
    list_case_evidence,
    update_evidence,
    upload_evidence_file,
)
router = APIRouter(tags=["evidence"])

# Allowed upload types: extension -> permitted content-types.
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_TYPES: dict[str, set[str]] = {
    "pdf": {"application/pdf"},
    "txt": {"text/plain"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "png": {"image/png"},
}


@router.post("/cases/{case_id}/evidence", response_model=CaseEvidenceCreateResponse, status_code=201)
def add_evidence_endpoint(
    case_id: int,
    payload: CaseEvidenceCreateRequest,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """Add a new evidence item to a case and link it via CollectedFor."""
    try:
        return add_case_evidence(db, case_id, payload, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/cases/{case_id}/evidence", response_model=CaseEvidenceListResponse)
def list_evidence_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """List all evidence items collected for a case."""
    try:
        return list_case_evidence(db, case_id, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/evidence/{evidence_id}", response_model=EvidenceRead)
def get_evidence_endpoint(evidence_id: int, db=Depends(get_db)):
    """Fetch a single evidence item by its ID."""
    try:
        return get_evidence(db, evidence_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/evidence/{evidence_id}/file", response_model=EvidenceRead)
def upload_evidence_file_endpoint(
    evidence_id: int,
    file: UploadFile = File(...),
    db=Depends(get_db),
):
    """Attach a file to an evidence row, storing the object in S3 (AES256)."""
    ev = db.get(Evidence, evidence_id)
    if ev is None:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found.")

    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    content_type = (file.content_type or "").lower()

    allowed = _ALLOWED_TYPES.get(ext)
    if allowed is None or content_type not in allowed:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Allowed: pdf, txt, jpg, jpeg, png.",
        )

    # Read one byte past the limit so we can detect oversize without buffering more.
    content = file.file.read(_MAX_UPLOAD_BYTES + 1)
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit.")

    key = upload_evidence_file(content, evidence_id, content_type, ext)
    try:
        return attach_evidence_file(db, evidence_id, key, content_type, len(content))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/evidence/{evidence_id}", response_model=EvidenceRead)
def update_evidence_endpoint(
    evidence_id: int,
    description: str | None = None,
    location_id: int | None = None,
    collected_at: date | None = None,
    db=Depends(get_db),
):
    """Partially update an evidence record (description, location, collection date)."""
    try:
        return update_evidence(
            db,
            evidence_id,
            description=description,
            location_id=location_id,
            collected_at=collected_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
