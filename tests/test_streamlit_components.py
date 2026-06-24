import sys, os, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "streamlit_app"))


def _fake_streamlit(session):
    mod = types.ModuleType("streamlit")
    mod.session_state = session
    return mod


def test_api_patch_success(monkeypatch):
    import utils
    captured = {}

    class FakeResp:
        ok = True
        def json(self): return {"ok": 1}

    def fake_patch(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return FakeResp()

    monkeypatch.setattr(utils, "st", _fake_streamlit({"base_url": "http://x", "jwt": "TKN"}))
    monkeypatch.setattr(utils.requests, "patch", fake_patch)

    data, err = utils.api_patch("/cases/1", {"status": "closed"})
    assert err is None
    assert data == {"ok": 1}
    assert captured["url"] == "http://x/cases/1"
    assert captured["headers"]["Authorization"] == "Bearer TKN"


def test_api_delete_ok(monkeypatch):
    import utils

    class FakeResp:
        ok = True
        status_code = 204
        text = ""
        def json(self): return {}

    monkeypatch.setattr(utils, "st", _fake_streamlit({"base_url": "http://x", "jwt": "T"}))
    monkeypatch.setattr(utils.requests, "delete", lambda *a, **k: FakeResp())
    ok, err = utils.api_delete("/cases/1/officers/2")
    assert ok is True and err is None


def test_api_post_file_sends_multipart(monkeypatch):
    import utils
    captured = {}

    class FakeResp:
        ok = True
        def json(self): return {"file_key": "k"}

    def fake_post(url, files=None, headers=None, timeout=None):
        captured["files"] = files
        captured["headers"] = headers
        return FakeResp()

    monkeypatch.setattr(utils, "st", _fake_streamlit({"base_url": "http://x", "jwt": "T"}))
    monkeypatch.setattr(utils.requests, "post", fake_post)
    data, err = utils.api_post_file("/evidence/1/file", b"abc", "a.pdf", "application/pdf")
    assert err is None and data == {"file_key": "k"}
    assert captured["files"]["file"][0] == "a.pdf"
    assert "Content-Type" not in captured["headers"]


import datetime
import pytest


def test_map_status():
    import components as c
    assert c.map_status("on_hold") == "hold"
    assert c.map_status("open") == "open"
    assert c.map_status(None) == "open"
    assert c.map_status(None, default="—") == "—"


def test_fmt_date():
    import components as c
    assert c.fmt_date(None) == "—"
    assert c.fmt_date("2026-06-24") == "24 JUN 2026"


def test_case_ref():
    import components as c
    assert c.case_ref("2026-06-24", 42) == "CIS/2026/0042"
    assert c.case_ref(None, None) == "CIS/----/"


def test_person_name():
    import components as c
    assert c.person_name({"first_name": "Asha", "last_name": "Rao"}) == "Asha Rao"
    assert c.person_name({"full_name": "K Mehra"}) == "K Mehra"
    assert c.person_name({"person_id": 7}) == "Person #7"
    assert c.person_name(None) == "—"


def test_build_person_payload_requires_exactly_one_address():
    import components as c
    with pytest.raises(ValueError):
        c.build_person_payload("A", "", "B", "M", None, "", "", address_id=None, address=None)
    with pytest.raises(ValueError):
        c.build_person_payload("A", "", "B", "M", None, "", "", address_id=1, address={"city": "X"})
    p = c.build_person_payload("A", "", "B", "M", datetime.date(2000, 1, 2), "", "999", address_id=3)
    assert p["address_id"] == 3 and p["birth_date"] == "2000-01-02"
    assert p["first_name"] == "A" and p["middle_name"] is None


def test_build_punishment_payload_validates():
    import components as c
    with pytest.raises(ValueError):
        c.build_punishment_payload([])
    with pytest.raises(ValueError):
        c.build_punishment_payload([1], jail_start=datetime.date(2026, 2, 1), jail_end=datetime.date(2026, 1, 1))
    p = c.build_punishment_payload([1, 2], fine=500, jail_start=datetime.date(2026, 1, 1))
    assert p["person_ids"] == [1, 2] and p["jail_start"] == "2026-01-01"


def test_build_case_payload_omits_optionals():
    import components as c
    p = c.build_case_payload("s", "Theft", 1, 2, datetime.date(2026, 6, 1))
    assert "initial_officer_id" not in p and "open_date" not in p
    assert p["occurred_at"] == "2026-06-01"


def test_theme_badge_and_card():
    import theme
    b = theme.badge("OPEN", "open")
    assert "OPEN" in b and "<span" in b and "#22c55e" in b
    card = theme.stat_card("OPEN CASES", 12, accent="#1860c4")
    assert "OPEN CASES" in card and ">12<" in card and "#1860c4" in card
    bar = theme.topbar("DSP R. Sharma", "24 JUN 2026 10:00")
    assert "RESTRICTED" in bar and "DSP R. Sharma" in bar
