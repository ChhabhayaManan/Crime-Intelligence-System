import sys, os, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "streamlit_app"))


class _FakeSessionState(dict):

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


def _fake_streamlit(session):
    mod = types.ModuleType("streamlit")
    mod.session_state = session if isinstance(session, _FakeSessionState) else _FakeSessionState(session)
    mod.reruns = []
    mod.rerun = lambda: mod.reruns.append(True)
    return mod


def test_api_patch_success(monkeypatch):
    import utils
    captured = {}

    class FakeResp:
        content = b"{}"
        ok = True
        status_code = 200
        def json(self): return {"ok": 1}

    def fake_request(method, url, headers=None, params=None, json=None, files=None, timeout=None):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return FakeResp()

    monkeypatch.setattr(utils, "st", _fake_streamlit({"base_url": "http://x", "access": "TKN", "refresh": "RTKN"}))
    monkeypatch.setattr(utils.requests, "request", fake_request)

    data, err = utils.api_patch("/cases/1", {"status": "closed"})
    assert err is None
    assert data == {"ok": 1}
    assert captured["method"] == "PATCH"
    assert captured["url"] == "http://x/cases/1"
    assert captured["json"] == {"status": "closed"}
    assert captured["headers"]["Authorization"] == "Bearer TKN"


def test_api_post_file_sends_multipart(monkeypatch):
    import utils
    captured = {}

    class FakeResp:
        content = b"{}"
        ok = True
        status_code = 200
        def json(self): return {"file_key": "k"}

    def fake_request(method, url, headers=None, params=None, json=None, files=None, timeout=None):
        captured["method"] = method
        captured["url"] = url
        captured["files"] = files
        captured["headers"] = headers
        return FakeResp()

    monkeypatch.setattr(utils, "st", _fake_streamlit({"base_url": "http://x", "access": "T", "refresh": "R"}))
    monkeypatch.setattr(utils.requests, "request", fake_request)
    data, err = utils.api_post_file("/evidence/1/file", b"abc", "a.pdf", "application/pdf")
    assert err is None and data == {"file_key": "k"}
    assert captured["method"] == "POST"
    assert captured["url"] == "http://x/evidence/1/file"
    assert captured["files"]["file"][0] == "a.pdf"
    assert "Content-Type" not in captured["headers"]


def test_request_retries_once_after_refresh_success(monkeypatch):
    import utils

    session = _FakeSessionState({"base_url": "http://x", "access": "OLD", "refresh": "RTKN"})
    monkeypatch.setattr(utils, "st", _fake_streamlit(session))

    main_calls = []
    refresh_calls = []

    class Resp401:
        ok = False
        content = b"{}"
        status_code = 401
        text = "unauthorized"
        def json(self): return {"detail": "Could not validate credentials."}

    class Resp200:
        content = b"{}"
        ok = True
        status_code = 200
        def json(self): return {"ok": "second"}

    class RefreshResp:
        content = b"{}"
        ok = True
        status_code = 200
        def json(self): return {"access_token": "NEW", "token_type": "bearer", "expires_at": "2026-01-01T00:00:00Z"}

    def fake_request(method, url, headers=None, params=None, json=None, files=None, timeout=None):
        main_calls.append({"method": method, "url": url, "headers": headers})
        return Resp401() if len(main_calls) == 1 else Resp200()

    def fake_post(url, json=None, headers=None, timeout=None):
        refresh_calls.append({"url": url, "json": json, "headers": headers})
        return RefreshResp()

    monkeypatch.setattr(utils.requests, "request", fake_request)
    monkeypatch.setattr(utils.requests, "post", fake_post)

    data, err = utils.api_get("/cases")

    assert err is None
    assert data == {"ok": "second"}

    assert len(main_calls) == 2
    assert main_calls[0]["headers"]["Authorization"] == "Bearer OLD"
    assert main_calls[1]["headers"]["Authorization"] == "Bearer NEW"

    assert len(refresh_calls) == 1
    assert refresh_calls[0]["url"] == "http://x/auth/refresh"
    assert refresh_calls[0]["json"] == {"refresh_token": "RTKN"}
    assert refresh_calls[0]["headers"] is None

    assert session["access"] == "NEW"


def test_request_retries_only_once_when_401_persists(monkeypatch):
    import utils

    session = _FakeSessionState({"base_url": "http://x", "access": "OLD", "refresh": "RTKN"})
    monkeypatch.setattr(utils, "st", _fake_streamlit(session))

    main_calls = []
    refresh_calls = []

    class Resp401:
        ok = False
        content = b"{}"
        status_code = 401
        text = "unauthorized"
        def json(self): return {"detail": "Could not validate credentials."}

    class RefreshResp:
        content = b"{}"
        ok = True
        status_code = 200
        def json(self): return {"access_token": "NEW", "token_type": "bearer", "expires_at": "2026-01-01T00:00:00Z"}

    def fake_request(method, url, headers=None, params=None, json=None, files=None, timeout=None):
        main_calls.append({"method": method, "url": url, "headers": headers})
        return Resp401()

    def fake_post(url, json=None, headers=None, timeout=None):
        refresh_calls.append({"url": url, "json": json, "headers": headers})
        return RefreshResp()

    monkeypatch.setattr(utils.requests, "request", fake_request)
    monkeypatch.setattr(utils.requests, "post", fake_post)

    data, err = utils.api_get("/cases")

    assert data is None
    assert "401" in err

    assert len(main_calls) == 2
    assert main_calls[1]["headers"]["Authorization"] == "Bearer NEW"
    assert len(refresh_calls) == 1


def test_request_clears_tokens_on_failed_refresh(monkeypatch):
    import utils

    session = _FakeSessionState({"base_url": "http://x", "access": "OLD", "refresh": "RTKN"})
    monkeypatch.setattr(utils, "st", _fake_streamlit(session))

    main_calls = []
    refresh_calls = []

    class Resp401:
        ok = False
        content = b"{}"
        status_code = 401
        text = "unauthorized"
        def json(self): return {"detail": "Could not validate credentials."}

    class RefreshFail:
        ok = False
        content = b"{}"
        status_code = 401
        text = "refresh failed"
        def json(self): return {"detail": "Could not validate credentials."}

    def fake_request(method, url, headers=None, params=None, json=None, files=None, timeout=None):
        main_calls.append({"method": method, "url": url, "headers": headers})
        return Resp401()

    def fake_post(url, json=None, headers=None, timeout=None):
        refresh_calls.append({"url": url, "json": json, "headers": headers})
        return RefreshFail()

    monkeypatch.setattr(utils.requests, "request", fake_request)
    monkeypatch.setattr(utils.requests, "post", fake_post)

    data, err = utils.api_get("/cases")

    assert data is None
    assert err is not None
    assert "401" in err

    assert len(main_calls) == 1
    assert len(refresh_calls) == 1

    assert session["access"] is None
    assert session["refresh"] is None


def test_request_without_refresh_token_does_not_attempt_refresh(monkeypatch):
    import utils

    session = _FakeSessionState({"base_url": "http://x", "access": "T", "refresh": None})
    monkeypatch.setattr(utils, "st", _fake_streamlit(session))

    main_calls = []
    refresh_calls = []

    class Resp401:
        ok = False
        content = b"{}"
        status_code = 401
        text = "unauthorized"
        def json(self): return {"detail": "Could not validate credentials."}

    def fake_request(method, url, headers=None, params=None, json=None, files=None, timeout=None):
        main_calls.append({"method": method, "url": url, "headers": headers})
        return Resp401()

    def fake_post(url, json=None, headers=None, timeout=None):
        refresh_calls.append(url)
        raise AssertionError("refresh must not be attempted without a refresh token")

    monkeypatch.setattr(utils.requests, "request", fake_request)
    monkeypatch.setattr(utils.requests, "post", fake_post)

    data, err = utils.api_get("/cases")

    assert data is None
    assert "401" in err
    assert len(main_calls) == 1
    assert refresh_calls == []
    assert session["access"] == "T"


def test_request_non_401_error_does_not_attempt_refresh(monkeypatch):
    import utils

    session = _FakeSessionState({"base_url": "http://x", "access": "T", "refresh": "RTKN"})
    monkeypatch.setattr(utils, "st", _fake_streamlit(session))

    main_calls = []
    refresh_calls = []

    class Resp403:
        ok = False
        content = b"{}"
        status_code = 403
        text = "forbidden"
        def json(self): return {"detail": "You can only change your own password."}

    def fake_request(method, url, headers=None, params=None, json=None, files=None, timeout=None):
        main_calls.append({"method": method, "url": url, "headers": headers})
        return Resp403()

    def fake_post(url, json=None, headers=None, timeout=None):
        refresh_calls.append(url)
        raise AssertionError("refresh must not be attempted for a non-401 status")

    monkeypatch.setattr(utils.requests, "request", fake_request)
    monkeypatch.setattr(utils.requests, "post", fake_post)

    data, err = utils.api_get("/cases")

    assert data is None
    assert "403" in err
    assert len(main_calls) == 1
    assert refresh_calls == []
    assert session["access"] == "T" and session["refresh"] == "RTKN"


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


def test_clear_pickers_only_drops_created_ids(monkeypatch):
    import forms
    state = _FakeSessionState({
        "case_loc_created_id": 5,
        "case_reporter_created_pid": 9,
        "case_loc_mode": "Create new",
        "access": "TKN",
    })
    monkeypatch.setattr(forms, "st", _fake_streamlit(state))
    forms._clear_pickers()
    assert "case_loc_created_id" not in state
    assert "case_reporter_created_pid" not in state
    assert state["case_loc_mode"] == "Create new"
    assert state["access"] == "TKN"


def test_label_options_keeps_same_named_people_apart():
    import forms
    opts = forms._label_options(
        [{"suspect_id": 1, "person": {"full_name": "Same Name"}},
         {"suspect_id": 2, "person": {"full_name": "Same Name"}}],
        "suspect_id",
    )
    assert sorted(opts.values()) == [1, 2]


def test_request_error_message_points_at_the_base_url(monkeypatch):
    import utils
    monkeypatch.setattr(utils, "st", _fake_streamlit({"base_url": "http://x", "access": None, "refresh": None}))

    def boom(*a, **kw):
        raise utils.requests.exceptions.ConnectionError("nope")

    monkeypatch.setattr(utils.requests, "request", boom)
    data, err = utils.api_get("/cases")
    assert data is None
    assert "Base URL" in err


def test_missing_base_url_falls_back_instead_of_crashing(monkeypatch):
    import utils
    captured = {}

    class Resp:
        ok = True
        status_code = 200
        content = b"{}"
        def json(self): return {}

    def fake_request(method, url, headers=None, params=None, json=None, files=None, timeout=None):
        captured["url"] = url
        return Resp()

    monkeypatch.setattr(utils, "st", _fake_streamlit({"base_url": None, "access": None, "refresh": None}))
    monkeypatch.setattr(utils.requests, "request", fake_request)
    utils.api_get("/cases")
    assert captured["url"].startswith("http://"), captured["url"]


def test_theme_exposes_one_palette_and_plot_layout():
    import theme
    assert theme.COLORS["bg"] in theme.stat_card("X", 1)
    assert theme.PLOT_LAYOUT["paper_bgcolor"] == theme.COLORS["bg"]
    assert not hasattr(theme, "micro_label")
