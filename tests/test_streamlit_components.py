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
