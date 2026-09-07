from types import SimpleNamespace

import pytest

import App.API.deps as deps


def _bind(monkeypatch, method):
    monkeypatch.setattr(deps, "ReadOnlySession", lambda: "READER")
    monkeypatch.setattr(deps, "WriteSession", lambda: "WRITER")
    request = SimpleNamespace(method=method, state=SimpleNamespace())
    db = next(deps.get_db(request))
    assert request.state.db is db, "the middleware needs the session on request.state"
    return db


@pytest.mark.parametrize("method", sorted(deps.READ_ONLY_METHODS))
def test_read_methods_use_the_reader(monkeypatch, method):
    assert _bind(monkeypatch, method) == "READER"


@pytest.mark.parametrize("method", ["POST", "PATCH", "PUT", "DELETE"])
def test_write_methods_use_the_writer(monkeypatch, method):
    assert _bind(monkeypatch, method) == "WRITER"


def test_get_db_does_not_commit_itself(monkeypatch):
    """The commit lives in the db_transaction middleware, not here."""
    closed = []
    monkeypatch.setattr(deps, "WriteSession", lambda: SimpleNamespace(
        commit=lambda: closed.append("commit"),
        rollback=lambda: closed.append("rollback"),
        close=lambda: closed.append("close"),
    ))
    request = SimpleNamespace(method="POST", state=SimpleNamespace())
    gen = deps.get_db(request)
    next(gen)
    list(gen)
    assert closed == []
