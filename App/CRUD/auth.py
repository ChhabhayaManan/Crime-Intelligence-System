"""
Functions for user authentication and JWT handling in the Crime Intelligence System.
- _hash_password: Hashes a plaintext password.
- _verify_password: Checks a plaintext password against a hash.
- CurrentUser: Holds the authenticated user's id and username.
- _create_access_token: Builds a short-lived access token and its expiry.
- _create_refresh_token: Builds a long-lived refresh token for a user.
- register_user: Registers a new user, rejecting duplicate usernames and emails.
- login_user: Verifies credentials, updates last_login and returns a token pair.
- refresh_access_token: Issues a new access token from a valid refresh token.
- change_password: Verifies the current password and sets a new one.
- get_current_user: FastAPI dependency resolving a bearer token to a CurrentUser.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from App.db.models import AppUser
from App.schema.core import (
    ChangePasswordRequest,
    TokenOut,
    TokenRefreshOut,
    UserLoginRequest,
    UserOut,
    UserRegisterRequest,
)


_jwt_secret = os.getenv("JWT_SECRET")
if not _jwt_secret:
    raise RuntimeError("JWT_SECRET environment variable is required.")
SECRET_KEY: str = _jwt_secret
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


_password_hash = PasswordHash.recommended()
_DUMMY_HASH = _password_hash.hash("dummypassword")


def _hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    username: str


def _create_access_token(user_id: int, username: str) -> tuple[str, datetime]:
    now = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "username": username,
        "typ": "access",
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, expires_at


def _create_refresh_token(user: AppUser) -> str:
    now = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user.user_id),
        "username": user.username,
        "typ": "refresh",
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def register_user(db: Session, payload: UserRegisterRequest) -> AppUser:
    if db.query(AppUser).filter(AppUser.username == payload.username).first():
        raise ValueError(f"Username '{payload.username}' is already taken.")
    if db.query(AppUser).filter(AppUser.email == payload.email).first():
        raise ValueError(f"Email '{payload.email}' is already registered.")

    user = AppUser(
        username=payload.username,
        email=payload.email,
        mobile_number=payload.mobile_number,
        hashed_password=_hash_password(payload.password),
    )
    try:
        with db.begin_nested():
            db.add(user)
            db.flush()
    except IntegrityError:
        raise ValueError("Username or email is already registered.") from None
    return user


def login_user(db: Session, payload: UserLoginRequest) -> TokenOut:
    user = db.query(AppUser).filter(AppUser.username == payload.username).first()

    if not user:
        _verify_password(payload.password, _DUMMY_HASH)
        raise ValueError("Incorrect username or password.")

    if not _verify_password(payload.password, user.hashed_password):
        raise ValueError("Incorrect username or password.")

    user.last_login = datetime.now(tz=timezone.utc)
    db.flush()

    access_token, expires_at = _create_access_token(user.user_id, user.username)
    refresh_token = _create_refresh_token(user)
    return TokenOut(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_at=expires_at,
    )


def refresh_access_token(db: Session, refresh_token: str) -> TokenRefreshOut:
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
    except InvalidTokenError:
        raise ValueError("Could not validate credentials.") from None

    if payload.get("typ") != "refresh":
        raise ValueError("Could not validate credentials.")

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise ValueError("Could not validate credentials.") from None

    user = db.get(AppUser, user_id)
    if user is None:
        raise ValueError("Could not validate credentials.")

    access_token, expires_at = _create_access_token(user.user_id, user.username)
    return TokenRefreshOut(
        access_token=access_token, token_type="bearer", expires_at=expires_at
    )


def change_password(db: Session, payload: ChangePasswordRequest) -> UserOut:
    user = db.query(AppUser).filter(AppUser.username == payload.username).first()

    if not user:
        _verify_password(payload.current_password, _DUMMY_HASH)
        raise ValueError("Incorrect username or current password.")

    if not _verify_password(payload.current_password, user.hashed_password):
        raise ValueError("Incorrect username or current password.")

    user.hashed_password = _hash_password(payload.new_password)
    db.flush()

    return UserOut(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        mobile_number=user.mobile_number,
    )


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except InvalidTokenError:
        raise credentials_exception from None

    if payload.get("typ") != "access":
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    username: str | None = payload.get("username")
    if user_id is None or username is None:
        raise credentials_exception

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise credentials_exception from None

    return CurrentUser(user_id=user_id_int, username=username)
