"""st.dialog create/edit forms + entity pickers."""
import streamlit as st
import components as c
from utils import api_get, api_post, api_patch, api_post_file, api_delete

GENDERS = ["", "M", "F", "O"]
ARREST = ["wanted", "arrested", "released"]


# ── Subforms (no API) ─────────────────────────────────────────────────────────
def address_subform(key):
    """Render address inputs; return AddressCreate dict (city/state/pin/country required)."""
    street = st.text_input("Street", key=f"{key}_street")
    col1, col2 = st.columns(2)
    city = col1.text_input("City *", key=f"{key}_city")
    state = col2.text_input("State *", key=f"{key}_state")
    col3, col4 = st.columns(2)
    pin = col3.text_input("PIN code *", key=f"{key}_pin")
    country = col4.text_input("Country *", value="India", key=f"{key}_country")
    if not (city and state and pin and country):
        return None
    return c.build_address_payload(street, city, state, pin, country)


# ── Pickers ───────────────────────────────────────────────────────────────────
def address_picker(label, key):
    """Search existing addresses or create one inline. Returns address_id or None."""
    st.markdown(f"**{label}**")
    mode = st.radio("Source", ["Existing", "Create new"], horizontal=True,
                    key=f"{key}_mode", label_visibility="collapsed")
    if mode == "Existing":
        city = st.text_input("Filter by city", key=f"{key}_filter")
        data, err = api_get("/addresses", {"city": city, "page_size": 50} if city else {"page_size": 50})
        if err:
            st.error(err)
            return None
        items = data.get("items", [])
        if not items:
            st.caption("No addresses. Try another city or create new.")
            return None
        opts = {f"#{a['address_id']} — {c.fmt_addr(a)}": a["address_id"] for a in items}
        choice = st.selectbox("Select address", list(opts.keys()), key=f"{key}_sel")
        return opts.get(choice)
    # Create new
    created_key = f"{key}_created_id"
    if st.session_state.get(created_key):
        st.success(f"Address #{st.session_state[created_key]} created.")
        return st.session_state[created_key]
    payload = address_subform(f"{key}_new")
    if payload and st.button("Save address", key=f"{key}_save"):
        data, err = api_post("/addresses", payload)
        if err:
            st.error(err)
            return None
        st.session_state[created_key] = data["address_id"]
        st.success(f"Address #{data['address_id']} created.")
        return data["address_id"]
    return None


def person_picker(label, key, role=None):
    """Search existing persons or create inline. Returns person_id or None."""
    st.markdown(f"**{label}**")
    mode = st.radio("Source", ["Existing", "Create new"], horizontal=True,
                    key=f"{key}_mode", label_visibility="collapsed")
    if mode == "Existing":
        q = st.text_input("Search by name", key=f"{key}_q")
        params = {"page_size": 50}
        if q:
            params["query"] = q
        if role:
            params["role"] = role
        data, err = api_get("/persons", params)
        if err:
            st.error(err)
            return None
        items = data.get("items", [])
        if not items:
            st.caption("No matches.")
            return None
        opts = {f"#{p['person_id']} — {c.person_name(p)}": p["person_id"] for p in items}
        choice = st.selectbox("Select person", list(opts.keys()), key=f"{key}_sel")
        return opts.get(choice)
    # Create new person (needs address)
    col1, col2, col3 = st.columns(3)
    first = col1.text_input("First name", key=f"{key}_f")
    middle = col2.text_input("Middle", key=f"{key}_m")
    last = col3.text_input("Last name", key=f"{key}_l")
    col4, col5 = st.columns(2)
    gender = col4.selectbox("Gender", GENDERS, key=f"{key}_g")
    birth = col5.date_input("Birth date", value=None, key=f"{key}_b")
    occupation = st.text_input("Occupation", key=f"{key}_occ")
    contact = st.text_input("Contact number", key=f"{key}_c")
    addr_id = address_picker("Address", f"{key}_addr")
    created_key = f"{key}_created_pid"
    if st.session_state.get(created_key):
        st.success(f"Person #{st.session_state[created_key]} created.")
        return st.session_state[created_key]
    if addr_id and st.button("Save person", key=f"{key}_save"):
        try:
            payload = c.build_person_payload(first, middle, last, gender, birth,
                                             occupation, contact, address_id=addr_id)
        except ValueError as e:
            st.error(str(e))
            return None
        data, err = api_post("/persons", payload)
        if err:
            st.error(err)
            return None
        pid = data["person_id"]
        st.session_state[created_key] = pid
        st.success(f"Person #{pid} created.")
        return pid
    return None


# ── Top-level create dialogs ──────────────────────────────────────────────────
@st.dialog("New Address")
def dialog_new_address():
    payload = address_subform("dlg_addr")
    if st.button("Create address", type="primary", disabled=payload is None):
        data, err = api_post("/addresses", payload)
        if err:
            st.error(err)
        else:
            st.success(f"Created address #{data['address_id']}.")
            st.rerun()


@st.dialog("New Person")
def dialog_new_person():
    col1, col2, col3 = st.columns(3)
    first = col1.text_input("First name")
    middle = col2.text_input("Middle")
    last = col3.text_input("Last name")
    col4, col5 = st.columns(2)
    gender = col4.selectbox("Gender", GENDERS)
    birth = col5.date_input("Birth date", value=None)
    occupation = st.text_input("Occupation")
    contact = st.text_input("Contact number")
    st.divider()
    addr_id = address_picker("Address", "dlg_person_addr")
    if st.button("Create person", type="primary", disabled=not addr_id):
        try:
            payload = c.build_person_payload(first, middle, last, gender, birth,
                                             occupation, contact, address_id=addr_id)
        except ValueError as e:
            st.error(str(e))
            return
        data, err = api_post("/persons", payload)
        if err:
            st.error(err)
        else:
            st.success(f"Created person #{data['person_id']}.")
            st.rerun()


@st.dialog("New Case")
def dialog_new_case():
    summary = st.text_area("Summary / complaint *", max_chars=255)
    col1, col2 = st.columns(2)
    crime_type = col1.text_input("Crime type *")
    occurred_at = col2.date_input("Crime date *", value=None)
    open_date = st.date_input("Open date (default today)", value=None)
    st.divider()
    reporter_id = person_picker("Reporter *", "case_reporter")
    st.divider()
    location_id = address_picker("Crime location *", "case_loc")
    st.divider()
    officer_id = person_picker("Initial officer (optional)", "case_off", role="officer")
    ready = bool(summary and crime_type and occurred_at and reporter_id and location_id)
    if st.button("Open case", type="primary", disabled=not ready):
        payload = c.build_case_payload(summary, crime_type, location_id, reporter_id,
                                       occurred_at, initial_officer_id=officer_id,
                                       open_date=open_date)
        data, err = api_post("/cases", payload)
        if err:
            st.error(err)
        else:
            st.success(f"Opened case #{data['case_id']} ({data.get('open_date')}).")
            st.rerun()
