import os
import streamlit as st
import requests

_DEFAULT_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


def setup_sidebar():
    st.session_state.setdefault("base_url", _DEFAULT_BASE)
    st.session_state.setdefault("access", None)
    st.session_state.setdefault("refresh", None)
    st.session_state.setdefault("username_display", "")

    with st.sidebar:
        st.text_input("API Base URL", key="base_url")
        if st.session_state.access:
            st.success(f"**{st.session_state.username_display}**")
            if st.button("Logout", key="sidebar_logout"):
                st.session_state.access = None
                st.session_state.refresh = None
                st.session_state.username_display = ""
                st.rerun()
        else:
            st.warning("Not logged in")


def require_auth():
    setup_sidebar()
    if not st.session_state.get("access"):
        st.error("Not logged in. Go to **Home** to authenticate.")
        st.stop()


def _request(method, path, *, params=None, json=None, files=None, timeout=30):
    base = st.session_state.get("base_url") or _DEFAULT_BASE
    t = (5, timeout) if isinstance(timeout, (int, float)) else timeout

    def _send():
        access = st.session_state.get("access")
        headers = {"Authorization": f"Bearer {access}"} if access else {}
        return requests.request(
            method, f"{base}{path}", headers=headers, params=params, json=json, files=files, timeout=t
        )

    res = _send()
    if res.status_code == 401 and st.session_state.get("refresh"):
        try:
            refresh_res = requests.post(
                f"{base}/auth/refresh",
                json={"refresh_token": st.session_state.refresh},
                timeout=t,
            )
        except requests.exceptions.RequestException:
            refresh_res = None
        if refresh_res is not None and refresh_res.ok:
            st.session_state.access = refresh_res.json().get("access_token")
            res = _send()
        else:
            st.session_state.access = None
            st.session_state.refresh = None
            st.rerun()
    return res


def _call(method, path, **kw):
    try:
        res = _request(method, path, **kw)
    except requests.exceptions.RequestException as exc:
        return None, (
            f"Cannot reach the backend ({type(exc).__name__}). "
            "Check the API Base URL in the sidebar."
        )
    if res.ok:
        return (res.json() if res.content else None), None
    try:
        detail = res.json().get("detail", res.text[:200])
    except Exception:
        detail = res.text[:200]
    return None, f"HTTP {res.status_code}: {detail}"


def api_get(path, params=None, timeout=30):
    return _call("GET", path, params=params, timeout=timeout)


def api_post(path, payload, timeout=45):
    return _call("POST", path, json=payload, timeout=timeout)


def api_patch(path, payload, timeout=45):
    return _call("PATCH", path, json=payload, timeout=timeout)


def api_post_file(path, file_bytes, filename, content_type, timeout=60):
    files = {"file": (filename, file_bytes, content_type)}
    return _call("POST", path, files=files, timeout=timeout)


@st.cache_data(ttl=30, show_spinner=False)
def _cached_get(path, items, base, token):
    return _call("GET", path, params=dict(items))


def api_get_cached(path, params=None):
    return _cached_get(
        path,
        tuple(sorted((params or {}).items())),
        st.session_state.get("base_url"),
        st.session_state.get("access"),
    )
