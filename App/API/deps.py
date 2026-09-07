from typing import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from App.db.session import ReadOnlySession, Session as WriteSession

READ_ONLY_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_db(request: Request) -> Generator[Session, None, None]:
    db = (ReadOnlySession if request.method in READ_ONLY_METHODS else WriteSession)()
    request.state.db = db
    yield db
