import os
import streamlit as st
import requests

_DEFAULT_BASE = os.getenv("API_BASE_URL",
                          "http://crime-is-alb-1406661986.ap-south-1.elb.amazonaws.com/api/v1")


def setup_sidebar():
    """Render sidebar (base URL + auth status) on every page."""
    if "base_url" not in st.session_state:
        st.session_state.base_url = _DEFAULT_BASE
    if "jwt" not in st.session_state:
        st.session_state.jwt = None
    if "username_display" not in st.session_state:
        st.session_state.username_display = ""

    with st.sidebar:
        st.markdown("### ⚙️ Config")
        new_url = st.text_input(
            "API Base URL",
            value=st.session_state.base_url,
            key="sidebar_base_url_input",
        )
        if new_url != st.session_state.base_url:
            st.session_state.base_url = new_url

        st.divider()
        if st.session_state.jwt:
            st.success(f"**{st.session_state.username_display}**")
            if st.button("Logout", key="sidebar_logout"):
                st.session_state.jwt = None
                st.session_state.username_display = ""
                st.rerun()
        else:
            st.warning("Not logged in")


def require_auth():
    """Stop page render if not authenticated."""
    setup_sidebar()
    if not st.session_state.get("jwt"):
        st.error("Not logged in. Go to **Home** to authenticate.")
        st.stop()


def api_get(path, params=None, timeout=30):
    """GET request with consistent error handling. Returns (data_dict_or_list, error_str_or_None)."""
    base = st.session_state.get("base_url", _DEFAULT_BASE)
    jwt = st.session_state.get("jwt")
    headers = {"Authorization": f"Bearer {jwt}"} if jwt else {}
    # (connect_timeout, read_timeout) — fail fast on unreachable host, wait longer for DB queries
    t = (5, timeout) if isinstance(timeout, (int, float)) else timeout
    try:
        res = requests.get(f"{base}{path}", headers=headers, params=params, timeout=t)
        if res.ok:
            return res.json(), None
        try:
            detail = res.json().get("detail", res.text[:200])
        except Exception:
            detail = res.text[:200]
        return None, f"HTTP {res.status_code}: {detail}"
    except requests.exceptions.ConnectTimeout:
        return None, f"Cannot reach API at **{base}** (connect timeout). Check the Base URL in the sidebar."
    except requests.exceptions.ConnectionError:
        return None, f"Cannot connect to API at **{base}**. Is the backend running? Check the Base URL in the sidebar."
    except requests.exceptions.ReadTimeout:
        return None, f"API at **{base}** is taking too long to respond ({timeout}s). Try again — may be a cold start."


def api_post(path, payload, timeout=45):
    """POST request with consistent error handling. Returns (data_dict_or_None, error_str_or_None)."""
    base = st.session_state.get("base_url", _DEFAULT_BASE)
    jwt = st.session_state.get("jwt")
    headers = {"Authorization": f"Bearer {jwt}"} if jwt else {}
    t = (5, timeout) if isinstance(timeout, (int, float)) else timeout
    try:
        res = requests.post(f"{base}{path}", json=payload, headers=headers, timeout=t)
        if res.ok:
            return res.json(), None
        try:
            detail = res.json().get("detail", res.text[:200])
        except Exception:
            detail = res.text[:200]
        return None, detail
    except requests.exceptions.ConnectTimeout:
        return None, f"Cannot reach API at **{base}** (connect timeout). Check the Base URL in the sidebar."
    except requests.exceptions.ConnectionError:
        return None, f"Cannot connect to API at **{base}**. Is the backend running? Check the Base URL in the sidebar."
    except requests.exceptions.ReadTimeout:
        return None, f"API at **{base}** is taking too long ({timeout}s). Auth operations (Argon2) can be slow — try again."


def api_patch(path, payload, timeout=45):
    """PATCH request. Returns (data_dict_or_None, error_str_or_None)."""
    base = st.session_state.get("base_url", _DEFAULT_BASE)
    jwt = st.session_state.get("jwt")
    headers = {"Authorization": f"Bearer {jwt}"} if jwt else {}
    t = (5, timeout) if isinstance(timeout, (int, float)) else timeout
    try:
        res = requests.patch(f"{base}{path}", json=payload, headers=headers, timeout=t)
        if res.ok:
            return res.json(), None
        try:
            detail = res.json().get("detail", res.text[:200])
        except Exception:
            detail = res.text[:200]
        return None, detail
    except requests.exceptions.ConnectTimeout:
        return None, f"Cannot reach API at **{base}** (connect timeout)."
    except requests.exceptions.ConnectionError:
        return None, f"Cannot connect to API at **{base}**. Is the backend running?"
    except requests.exceptions.ReadTimeout:
        return None, f"API at **{base}** is taking too long ({timeout}s). Try again."


def api_delete(path, timeout=30):
    """DELETE request. Returns (ok_bool, error_str_or_None)."""
    base = st.session_state.get("base_url", _DEFAULT_BASE)
    jwt = st.session_state.get("jwt")
    headers = {"Authorization": f"Bearer {jwt}"} if jwt else {}
    t = (5, timeout) if isinstance(timeout, (int, float)) else timeout
    try:
        res = requests.delete(f"{base}{path}", headers=headers, timeout=t)
        if res.ok:
            return True, None
        try:
            detail = res.json().get("detail", res.text[:200])
        except Exception:
            detail = res.text[:200]
        return False, f"HTTP {res.status_code}: {detail}"
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to API at **{base}**."
    except requests.exceptions.Timeout:
        return False, f"API at **{base}** timed out."


def api_post_file(path, file_bytes, filename, content_type, timeout=60):
    """Multipart file POST (no JSON body). Returns (data_dict_or_None, error_str_or_None)."""
    base = st.session_state.get("base_url", _DEFAULT_BASE)
    jwt = st.session_state.get("jwt")
    headers = {"Authorization": f"Bearer {jwt}"} if jwt else {}
    files = {"file": (filename, file_bytes, content_type)}
    t = (5, timeout) if isinstance(timeout, (int, float)) else timeout
    try:
        res = requests.post(f"{base}{path}", files=files, headers=headers, timeout=t)
        if res.ok:
            return res.json(), None
        try:
            detail = res.json().get("detail", res.text[:200])
        except Exception:
            detail = res.text[:200]
        return None, detail
    except requests.exceptions.ConnectionError:
        return None, f"Cannot connect to API at **{base}**."
    except requests.exceptions.Timeout:
        return None, f"Upload to **{base}** timed out ({timeout}s)."
