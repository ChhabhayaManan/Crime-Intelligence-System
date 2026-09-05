from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from App.API.deps import get_db
from App.schema.case import CrimeHotspotQuery, CrimeHotspotResponse
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
    CurrentUser,
    change_password,
    get_current_user,
    login_user,
    refresh_access_token,
    register_user,
)

router = APIRouter(tags=["analytics"])
auth_router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/analytics/hotspots", response_model=CrimeHotspotResponse)
def crime_hotspots_endpoint(
    city: str | None = Query(default=None),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db=Depends(get_db),
):
    query = CrimeHotspotQuery(city=city, from_date=from_date, to_date=to_date)
    return get_crime_hotspots(db, query)


@auth_router.post(
    "/register", response_model=UserOut, status_code=status.HTTP_201_CREATED
)
def register_endpoint(payload: UserRegisterRequest, db=Depends(get_db)):
    return UserOut.model_validate(register_user(db, payload))


@auth_router.post("/login", response_model=TokenOut)
def login_endpoint(payload: UserLoginRequest, db=Depends(get_db)):
    return login_user(db, payload)


@auth_router.post("/refresh", response_model=TokenRefreshOut)
def refresh_endpoint(payload: TokenRefreshRequest, db=Depends(get_db)):
    return refresh_access_token(db, payload.refresh_token)


@auth_router.post("/change-password", response_model=UserOut)
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
    return change_password(db, payload)
