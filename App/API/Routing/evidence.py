from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from App.API.deps import get_db
from App.db.models import Evidence
from App.schema.case import (
    CaseEvidenceCreateRequest,
    CaseEvidenceCreateResponse,
    CaseEvidenceListResponse,
    CaseEvidenceUpdateRequest,
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

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
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
    try:
        return list_case_evidence(db, case_id, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/evidence/{evidence_id}", response_model=EvidenceRead)
def get_evidence_endpoint(evidence_id: int, db=Depends(get_db)):
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
    payload: CaseEvidenceUpdateRequest,
    db=Depends(get_db),
):
    try:
        return update_evidence(db, evidence_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
