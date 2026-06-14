"""
system.py
---------
FastAPI router for Analytics and Authentication endpoints.

Analytics
---------
  GET  /cases/{case_id}/snapshot    - case snapshot (evidence + witnesses + suspects)
  GET  /analytics/hotspots          - crime hotspot aggregation

Auth
----
  POST /auth/register               - register new user (returns UserOut)
  POST /auth/login                  - login, returns JWT token
  POST /auth/change-password        - change password (requires valid JWT)
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from App.API.deps import get_db
from App.CRUD.auth import get_current_active_user
from App.db.models import AppUser
from App.schema.case import (
    CaseEvidenceWitnessSuspectResponse,
    CrimeHotspotQuery,
    CrimeHotspotResponse,
)
from App.schema.core import (
    ChangePasswordRequest,
    TokenOut,
    UserLoginRequest,
    UserOut,
    UserRegisterRequest,
)
from App.CRUD.analytics import (
    get_case_evidence_witness_suspect,
    get_crime_hotspots,
)
from App.CRUD.auth import (
    change_password,
    login_user,
    register_user,
)

router = APIRouter(tags=["system"])


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@router.get("/cases/{case_id}/snapshot", response_model=CaseEvidenceWitnessSuspectResponse)
def case_snapshot_endpoint(
    case_id: int,
    open_date: date | None = Query(default=None),
    db=Depends(get_db),
):
    """Return a combined snapshot of a case's evidence, witnesses, and suspects."""
    try:
        return get_case_evidence_witness_suspect(db, case_id, open_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/analytics/hotspots", response_model=CrimeHotspotResponse)
def crime_hotspots_endpoint(
    city: str | None = Query(default=None),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db=Depends(get_db),
):
    """Aggregate case counts by city and return locations sorted by crime frequency."""
    try:
        query = CrimeHotspotQuery(city=city, from_date=from_date, to_date=to_date)
        return get_crime_hotspots(db, query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# Auth - Register
# ---------------------------------------------------------------------------

@router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_endpoint(payload: UserRegisterRequest, db=Depends(get_db)):
    """Register a new user. Role defaults to 'viewer' and cannot be set via API."""
    try:
        user = register_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return UserOut(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        mobile_number=getattr(user, "mobile_number", None),
        role=user.role,
        is_active=user.is_active,
    )


# ---------------------------------------------------------------------------
# Auth - Login
# ---------------------------------------------------------------------------

@router.post("/auth/login", response_model=TokenOut, status_code=status.HTTP_200_OK)
def login_endpoint(payload: UserLoginRequest, db=Depends(get_db)):
    """Validate credentials and return a signed JWT access token."""
    try:
        return login_user(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# Auth - Change Password (requires login)
# ---------------------------------------------------------------------------

@router.post("/auth/change-password", response_model=UserOut, status_code=status.HTTP_200_OK)
def change_password_endpoint(
    payload: ChangePasswordRequest,
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_active_user),
):
    """Change the password for the authenticated user."""
    if current_user.username != payload.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only change your own password.",
        )
    try:
        return change_password(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


