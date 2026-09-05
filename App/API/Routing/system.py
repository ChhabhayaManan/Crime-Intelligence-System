from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import date

from App.API.deps import get_db
from App.CRUD.auth import CurrentUser, get_current_user
from App.schema.case import (
    CrimeHotspotQuery,
    CrimeHotspotResponse,
)
from App.schema.core import (
    ChangePasswordRequest,
    TokenOut,
    TokenRefreshOut,
    TokenRefreshRequest,
    UserLoginRequest,
    UserOut,
    UserRegisterRequest,
)
from App.CRUD.analytics import get_crime_hotspots
from App.CRUD.auth import (
    change_password,
    login_user,
    refresh_access_token,
    register_user,
)

router = APIRouter(tags=["system"])


@router.get("/analytics/hotspots", response_model=CrimeHotspotResponse)
def crime_hotspots_endpoint(
    city: str | None = Query(default=None),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db=Depends(get_db),
):
    try:
        query = CrimeHotspotQuery(city=city, from_date=from_date, to_date=to_date)
        return get_crime_hotspots(db, query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_endpoint(payload: UserRegisterRequest, db=Depends(get_db)):
    try:
        user = register_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return UserOut(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        mobile_number=getattr(user, "mobile_number", None),
    )


@router.post("/auth/login", response_model=TokenOut, status_code=status.HTTP_200_OK)
def login_endpoint(payload: UserLoginRequest, db=Depends(get_db)):
    try:
        return login_user(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/auth/refresh", response_model=TokenRefreshOut, status_code=status.HTTP_200_OK)
def refresh_endpoint(payload: TokenRefreshRequest, db=Depends(get_db)):
    try:
        return refresh_access_token(db, payload.refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/auth/change-password", response_model=UserOut, status_code=status.HTTP_200_OK)
def change_password_endpoint(
    payload: ChangePasswordRequest,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if current_user.username != payload.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only change your own password.",
        )
    try:
        return change_password(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
