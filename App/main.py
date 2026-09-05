import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from App.API import api_router
from App.CRUD.auth import AuthError
from App.CRUD.common import NotFoundError
from App.db.session import get_engine, get_reader_engine

app = FastAPI(
    title="Crime Tracking & Analysis API",
    version="2.0.0",
    description="REST endpoints for the Crime-Tracking-and-Analysis-Database.",
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
    allow_credentials="*" not in allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


def _error(status_code: int, detail: str, **kw) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail}, **kw)


@app.exception_handler(NotFoundError)
def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return _error(404, str(exc))


@app.exception_handler(AuthError)
def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    return _error(401, str(exc), headers={"WWW-Authenticate": "Bearer"})


@app.exception_handler(ValueError)
def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return _error(400, str(exc))


@app.exception_handler(IntegrityError)
def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    return _error(409, "Request conflicts with existing data.")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    checks: dict[str, str] = {}
    overall = "ok"

    for name, factory, failed in (
        ("writer", get_engine, "unhealthy"),
        ("reader", get_reader_engine, "degraded"),
    ):
        try:
            with factory().connect() as conn:
                conn.execute(text("SELECT 1"))
            checks[name] = "ok"
        except Exception:
            checks[name] = "fail"
            if failed == "unhealthy" or overall == "ok":
                overall = failed

    return JSONResponse(
        status_code=503 if overall == "unhealthy" else 200,
        content={"status": overall, "checks": checks},
    )
