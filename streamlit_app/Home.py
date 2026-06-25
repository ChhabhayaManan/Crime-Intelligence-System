import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from utils import setup_sidebar, api_post

st.set_page_config(page_title="CIS — Crime Intelligence System", page_icon="🔷", layout="wide")

if "jwt" not in st.session_state:
    st.session_state.jwt = None
if "username_display" not in st.session_state:
    st.session_state.username_display = ""

setup_sidebar()

st.markdown("## 🔷 CIS — Crime Intelligence System")
st.caption("RESTRICTED ACCESS — Authorised personnel only.")

if st.session_state.jwt:
    st.success(f"Authenticated as **{st.session_state.username_display}**. Use the sidebar to navigate.")
    st.stop()

tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

# ── Login ──
with tab_login:
    col1, col2 = st.columns([1, 1])
    with col1:
        username = st.text_input("Username / Service No.", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("AUTHENTICATE", type="primary", use_container_width=True):
            if not username or not password:
                st.error("Enter username and password.")
            else:
                with st.spinner("Authenticating..."):
                    data, err = api_post("/auth/login", {"username": username, "password": password})
                if err:
                    st.error(err)
                else:
                    st.session_state.jwt = data.get("access_token")
                    st.session_state.username_display = username
                    st.success("Authenticated. Navigate using the sidebar.")
                    st.rerun()

# ── Register ──
with tab_register:
    col1, col2 = st.columns([1, 1])
    with col1:
        r_user    = st.text_input("Username", key="reg_user", help="Min 3 characters")
        r_email   = st.text_input("Email", key="reg_email")
        r_mobile  = st.text_input("Mobile Number (optional)", key="reg_mobile")
        r_pass    = st.text_input("Password", type="password", key="reg_pass", help="Min 8 characters")
        r_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
        if st.button("CREATE ACCOUNT", type="primary", use_container_width=True):
            if not r_user or not r_email or not r_pass or not r_confirm:
                st.error("Username, email and password are required.")
            elif r_pass != r_confirm:
                st.error("Passwords do not match.")
            else:
                payload = {
                    "username": r_user,
                    "email": r_email,
                    "password": r_pass,
                    "confirm_password": r_confirm,
                }
                if r_mobile:
                    payload["mobile_number"] = r_mobile
                with st.spinner("Creating account..."):
                    data, err = api_post("/auth/register", payload)
                if err:
                    st.error(err)
                else:
                    st.success(f"Account created for **{r_user}**. Switch to Sign In tab.")
    with col2:
        st.info("New accounts are created as **viewer** role. An admin can upgrade your role directly in the database.")
