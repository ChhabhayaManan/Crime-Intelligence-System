from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import DeclarativeBase, Session as SASession, sessionmaker

SCHEMA = "crimedb"

_ENGINE_KW = {
    "pool_pre_ping": True,
    "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
    "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
    "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
    "connect_args": {"options": f"-csearch_path={SCHEMA}"},
}

_engine: Engine | None = None
_reader_engine: Engine | None = None

# base class for all ORM models
class Base(DeclarativeBase):
    pass

#get a primary engine url for read-write operations
def _writer_url() -> URL | str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    password = os.getenv("DB_PASSWORD")
    if not password:
        raise RuntimeError(
            "Set DATABASE_URL, or DB_PASSWORD together with DB_HOST/DB_NAME/DB_USER."
        )

    return URL.create(
        drivername="postgresql",
        username=os.getenv("DB_USER", "postgres"),
        password=password,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "crimedb"),
    )

# read write engine factory (primary engine factory)
def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(_writer_url(), **_ENGINE_KW)
    return _engine

# read only engine factory
def get_reader_engine() -> Engine:
    global _reader_engine
    if _reader_engine is None:
        writer = get_engine()
        host = os.getenv("DB_HOST_READ")
        if host and host != writer.url.host:
            _reader_engine = create_engine(writer.url.set(host=host), **_ENGINE_KW)
        else:
            _reader_engine = writer
    return _reader_engine

# session factory function
_session_factory = sessionmaker(class_=SASession, expire_on_commit=False)


def Session() -> SASession:
    return _session_factory(bind=get_engine())


def ReadOnlySession() -> SASession:
    return _session_factory(bind=get_reader_engine())


def __getattr__(name: str):
    if name == "engine":
        return get_engine()
    if name == "reader_engine":
        return get_reader_engine()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
