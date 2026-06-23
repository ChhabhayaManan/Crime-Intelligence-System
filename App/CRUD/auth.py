"""
auth.py
-------
Real authentication using pwdlib (Argon2) for password hashing
and PyJWT (HS256) for access tokens.

Public API
----------
  register_user(db, payload)   -> AppUser
  login_user(db, payload)      -> TokenOut
  change_password(db, payload) -> UserOut
  get_current_user(token, db)  -> AppUser   (FastAPI Depends target)
  get_current_active_user(user)-> AppUser   (FastAPI Depends target)
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from App.db.models import AppUser
from App.db.session import Session as SessionLocal
from App.schema.core import (
    ChangePasswordRequest,
    TokenOut,
    UserLoginRequest,
    UserOut,
    UserRegisterRequest,
)


# ---------------------------------------------------------------------------
# JWT config — JWT_SECRET injected from Secrets Manager in prod via ECS secrets;
# must also be set in compose.yaml / .env for local dev.
# ---------------------------------------------------------------------------

_jwt_secret = os.getenv("JWT_SECRET")
if not _jwt_secret:
    raise RuntimeError("JWT_SECRET environment variable is required.")
SECRET_KEY: str = _jwt_secret
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 1


# ---------------------------------------------------------------------------
# Password hashing (Argon2 via pwdlib)
# ---------------------------------------------------------------------------

_password_hash = PasswordHash.recommended()
_DUMMY_HASH = _password_hash.hash("dummypassword")  # timing-safe dummy


def _hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _create_access_token(user: AppUser) -> tuple[str, datetime]:
    """Return (encoded_token, expires_at)."""
    expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user.user_id),
        "username": user.username,
        "role": user.role,
        "exp": expires_at,
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, expires_at


# ---------------------------------------------------------------------------
# OAuth2 scheme  (tokenUrl must match the real login endpoint path)
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ---------------------------------------------------------------------------
# CRUD functions
# ---------------------------------------------------------------------------

def register_user(db: Session, payload: UserRegisterRequest) -> AppUser:
    """Hash password and insert a new AppUser. Raises ValueError on duplicates."""
    # Check uniqueness
    if db.query(AppUser).filter(AppUser.username == payload.username).first():
        raise ValueError(f"Username '{payload.username}' is already taken.")
    if db.query(AppUser).filter(AppUser.email == payload.email).first():
        raise ValueError(f"Email '{payload.email}' is already registered.")

    user = AppUser(
        username=payload.username,
        email=payload.email,
        mobile_number=payload.mobile_number,
        hashed_password=_hash_password(payload.password),
        role="viewer",          # role is NEVER set via API
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, payload: UserLoginRequest) -> TokenOut:
    """Verify credentials and return a JWT TokenOut. Always takes constant time."""
    user = db.query(AppUser).filter(AppUser.username == payload.username).first()

    if not user:
        # Timing-safe: still run hash verify even when user not found
        _verify_password(payload.password, _DUMMY_HASH)
        raise ValueError("Incorrect username or password.")

    if not _verify_password(payload.password, user.hashed_password):
        raise ValueError("Incorrect username or password.")

    if not user.is_active:
        raise ValueError("Account is disabled.")

    # Update last_login timestamp
    user.last_login = datetime.now(tz=timezone.utc)
    db.commit()

    token, expires_at = _create_access_token(user)
    return TokenOut(access_token=token, token_type="bearer", expires_at=expires_at)


def change_password(db: Session, payload: ChangePasswordRequest) -> UserOut:
    """Verify current password and store the new Argon2 hash."""
    user = db.query(AppUser).filter(AppUser.username == payload.username).first()

    if not user:
        _verify_password(payload.current_password, _DUMMY_HASH)
        raise ValueError("Incorrect username or current password.")

    if not _verify_password(payload.current_password, user.hashed_password):
        raise ValueError("Incorrect username or current password.")

    if not user.is_active:
        raise ValueError("Account is disabled.")

    user.hashed_password = _hash_password(payload.new_password)
    db.commit()
    db.refresh(user)

    return UserOut(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        mobile_number=getattr(user, "mobile_number", None),
        role=user.role,
        is_active=user.is_active,
    )


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> AppUser:
    """Decode JWT and return the live AppUser from DB (creates its own session)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    db = SessionLocal()
    try:
        user = db.get(AppUser, int(user_id))
    finally:
        db.close()

    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(
    current_user: Annotated[AppUser, Depends(get_current_user)],
) -> AppUser:
    """Raise 400 if the user account is disabled."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user.")
    return current_user


