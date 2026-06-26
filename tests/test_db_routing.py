"""
Unit tests for read/write session routing (App.db.session.RoutingSession).

Writes (flush / INSERT / UPDATE / DELETE) must bind to the primary engine;
plain SELECTs must bind to the read replica engine. These tests monkeypatch
the module-level engines to sentinels so routing decisions are observable
without a live database.
"""

from sqlalchemy import select, insert, update, delete, table, column

import App.db.session as db


_t = table("t", column("x"))


def _routing_session():
    """A RoutingSession instance with no real bind (get_bind is overridden)."""
    return db.RoutingSession()


def test_select_routes_to_reader(monkeypatch):
    monkeypatch.setattr(db, "engine", "WRITER")
    monkeypatch.setattr(db, "reader_engine", "READER")
    s = _routing_session()
    assert s.get_bind(clause=select(_t)) == "READER"


def test_insert_routes_to_writer(monkeypatch):
    monkeypatch.setattr(db, "engine", "WRITER")
    monkeypatch.setattr(db, "reader_engine", "READER")
    s = _routing_session()
    assert s.get_bind(clause=insert(_t)) == "WRITER"


def test_update_routes_to_writer(monkeypatch):
    monkeypatch.setattr(db, "engine", "WRITER")
    monkeypatch.setattr(db, "reader_engine", "READER")
    s = _routing_session()
    assert s.get_bind(clause=update(_t)) == "WRITER"


def test_delete_routes_to_writer(monkeypatch):
    monkeypatch.setattr(db, "engine", "WRITER")
    monkeypatch.setattr(db, "reader_engine", "READER")
    s = _routing_session()
    assert s.get_bind(clause=delete(_t)) == "WRITER"


def test_flush_routes_to_writer(monkeypatch):
    monkeypatch.setattr(db, "engine", "WRITER")
    monkeypatch.setattr(db, "reader_engine", "READER")
    s = _routing_session()
    # During a flush SQLAlchemy sets _flushing; a SELECT issued then must still
    # hit the primary so writes never leak to the replica.
    s._flushing = True
    assert s.get_bind(clause=select(_t)) == "WRITER"
