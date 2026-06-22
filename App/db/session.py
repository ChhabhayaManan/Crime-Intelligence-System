import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker


# Tables live in a named schema (not `public`) on RDS, so the search_path must be
# set on every connection or runtime queries fail to resolve. DB_SCHEMA defaults
# to `crimedb` to match setup_db.py.
_SCHEMA = os.getenv("DB_SCHEMA", "crimedb")
_CONNECT_ARGS = {"options": "-csearch_path=" + _SCHEMA}

database_url = os.getenv("DATABASE_URL")

if database_url:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args=_CONNECT_ARGS,
    )
else:
    engine = create_engine(
        URL.create(
            drivername="postgresql",
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "Ma314DBS@"),
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "crimedb"),
        ),
        pool_pre_ping=True,
        connect_args=_CONNECT_ARGS,
    )

Session = sessionmaker(bind=engine)
session = Session()


# --- Reader engine -----------------------------------------------------------
# A second engine pointed at the read replica (DB_HOST_READ), inheriting the
# writer's creds/port/db. If DB_HOST_READ is unset or equals the writer host,
# the reader falls back to the writer. Used only by /health/ready for now.
_reader_host = os.getenv("DB_HOST_READ")
# engine.url is a real URL object (keeps the password); str() would mask it as
# "***" and the reader would fail auth.
_writer_url = engine.url

if _reader_host and _reader_host != _writer_url.host:
    reader_engine = create_engine(
        _writer_url.set(host=_reader_host),
        pool_pre_ping=True,
        connect_args=_CONNECT_ARGS,
    )
else:
    reader_engine = engine

ReaderSession = sessionmaker(bind=reader_engine)

Base = declarative_base()
