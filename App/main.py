"""
main.py
-------
FastAPI application entry-point.
All domain routers are mounted under the /api/v1 prefix.
Health endpoints (/health, /health/ready) are mounted on the app directly,
public and unprefixed, for the ALB and CloudWatch/CI smoke tests.
"""

import os
from contextlib import asynccontextmanager

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from App.API import api_router
from App.db.models import AppUser, Person
from App.db.session import Session, engine, reader_engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Ensure auth table exists so login/register flows work even on older DB dumps.
    AppUser.__table__.create(bind=engine, checkfirst=True)
    yield


app = FastAPI(
    title="Crime Tracking & Analysis API",
    version="2.0.0",
    description="REST endpoints for the Crime-Tracking-and-Analysis-Database.",
    lifespan=lifespan,
)

_allowed_origins = os.getenv("ALLOWED_ORIGINS")
allow_origins = (
    [o.strip() for o in _allowed_origins.split(",") if o.strip()]
    if _allowed_origins
    else ["http://localhost:3000"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")



@app.get("/health")
def health():
    """Liveness probe — static 200, no DB dependency. The only path the ALB polls."""
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    """Deep readiness check with a per-check breakdown.

    Writer and ORM failures are fatal (unhealthy -> 503); reader and S3
    failures are non-fatal (degraded -> 200, writer-fallback).
    """
    checks: dict[str, str] = {}
    overall = "ok"

    # 1. Writer ping — fatal.
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["writer"] = "ok"
    except Exception:
        checks["writer"] = "fail"
        overall = "unhealthy"

    # 2. ORM round-trip — fatal.
    try:
        db = Session()
        try:
            db.execute(select(Person).limit(1)).first()
        finally:
            db.close()
        checks["orm"] = "ok"
    except Exception:
        checks["orm"] = "fail"
        overall = "unhealthy"

    # 3. Reader ping — non-fatal (degraded).
    try:
        with reader_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["reader"] = "ok"
    except Exception:
        checks["reader"] = "fail"
        if overall == "ok":
            overall = "degraded"

    # 4. S3 HeadBucket — non-fatal (degraded).
    bucket = os.getenv("S3_EVIDENCE_BUCKET")
    try:
        if not bucket:
            raise RuntimeError("S3_EVIDENCE_BUCKET not set")
        boto3.client("s3").head_bucket(Bucket=bucket)
        checks["s3"] = "ok"
    except Exception:
        checks["s3"] = "fail"
        if overall == "ok":
            overall = "degraded"

    status_code = 503 if overall == "unhealthy" else 200
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks},
    )
