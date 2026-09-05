from typing import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from App.db.session import ReadOnlySession, Session as WriteSession

_READ_ONLY_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_db(request: Request) -> Generator[Session, None, None]:
    read_only = request.method in _READ_ONLY_METHODS
    db = (ReadOnlySession if read_only else WriteSession)()
    try:
        yield db
        if not read_only:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
