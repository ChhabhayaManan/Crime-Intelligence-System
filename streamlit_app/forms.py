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


# ── Case child-record dialogs ─────────────────────────────────────────────────
@st.dialog("Add Evidence")
def dialog_add_evidence(case_id):
    desc = st.text_area("Description", max_chars=255)
    collected = st.date_input("Collected on", value=None)
    loc = address_picker("Location (optional)", f"evi_loc_{case_id}")
    up = st.file_uploader("Attach file (pdf/txt/jpg/png, ≤10MB)",
                          type=["pdf", "txt", "jpg", "jpeg", "png"])
    if st.button("Add evidence", type="primary"):
        payload = {"description": desc or None, "collected_at": c.iso(collected),
                   "location_id": loc}
        data, err = api_post(f"/cases/{case_id}/evidence", payload)
        if err:
            st.error(err)
            return
        eid = data["evidence_id"]
        if up is not None:
            _, ferr = api_post_file(f"/evidence/{eid}/file", up.getvalue(), up.name, up.type)
            if ferr:
                st.warning(f"Evidence #{eid} created but file failed: {ferr}")
                st.rerun()
                return
        st.success(f"Evidence #{eid} added.")
        st.rerun()


@st.dialog("Add Suspect")
def dialog_add_suspect(case_id, evidence):
    pid = person_picker("Suspect person", f"susp_{case_id}")
    desc = st.text_input("Physical description")
    contact = st.text_input("Family contact")
    arrest = st.selectbox("Arrest status", [""] + ARREST)
    ev_opts = {f"EV-{e['evidence_id']}": e["evidence_id"] for e in evidence}
    linked = st.multiselect("Link evidence", list(ev_opts.keys()))
    if st.button("Add suspect", type="primary", disabled=not pid):
        payload = {"person_id": pid, "physical_description": desc or None,
                   "family_contact": contact or None, "arrest_status": arrest or None,
                   "evidence_ids": [ev_opts[k] for k in linked]}
        data, err = api_post(f"/cases/{case_id}/suspects", payload)
        if err:
            st.error(err)
        else:
            st.success(f"Suspect #{data['suspect_id']} added.")
            st.rerun()


@st.dialog("Add Witness")
def dialog_add_witness(case_id):
    pid = person_picker("Witness person", f"wit_{case_id}")
    contact = st.text_input("Contact info")
    statement = st.text_area("Statement", max_chars=255)
    if st.button("Add witness", type="primary", disabled=not pid):
        payload = {"person_id": pid, "contact_info": contact or None,
                   "statement": statement or None}
        data, err = api_post(f"/cases/{case_id}/witnesses", payload)
        if err:
            st.error(err)
        else:
            st.success(f"Witness #{data['witness_id']} added.")
            st.rerun()


@st.dialog("Add Victim")
def dialog_add_victim(case_id):
    pid = person_picker("Victim person", f"vic_{case_id}")
    harm = st.text_area("Harm details", max_chars=255)
    contact = st.text_input("Family contact")
    if st.button("Add victim", type="primary", disabled=not pid):
        payload = {"person_id": pid, "harm_details": harm or None,
                   "family_contact": contact or None}
        data, err = api_post(f"/cases/{case_id}/victims", payload)
        if err:
            st.error(err)
        else:
            st.success(f"Victim #{data['victim_id']} added.")
            st.rerun()


@st.dialog("Record Testimony")
def dialog_record_testimony(case_id, witnesses, suspects):
    w_opts = {c.person_name(w.get("person")): w.get("witness_id") for w in witnesses}
    wname = st.selectbox("Witness", list(w_opts.keys()))
    text = st.text_area("Testimony *", max_chars=255)
    s_opts = {c.person_name(s.get("person")): s.get("suspect_id") for s in suspects}
    pointed = st.multiselect("Points to suspects", list(s_opts.keys()))
    if st.button("Record", type="primary", disabled=not (wname and text)):
        payload = {"testimony_text": text,
                   "pointed_suspects": [s_opts[k] for k in pointed]}
        _, err = api_post(f"/cases/{case_id}/witnesses/{w_opts[wname]}/testimony", payload)
        if err:
            st.error(err)
        else:
            st.success("Testimony recorded.")
            st.rerun()


@st.dialog("Add Trial")
def dialog_add_trial(case_id):
    judge = person_picker("Judge (optional)", f"judge_{case_id}")
    hearing = st.date_input("Hearing date", value=None)
    court = st.text_input("Court level")
    if st.button("Add trial", type="primary"):
        payload = {"judge_id": judge, "hearing_date": c.iso(hearing),
                   "court_level": court or None}
        data, err = api_post(f"/cases/{case_id}/trials", payload)
        if err:
            st.error(err)
        else:
            st.success(f"Trial #{data['trial_id']} created.")
            st.rerun()


@st.dialog("Add Hearing")
def dialog_add_hearing(case_id, trial_id):
    hearing = st.date_input("Hearing date", value=None)
    outcome = st.text_input("Outcome")
    if st.button("Add hearing", type="primary"):
        payload = {"hearing_date": c.iso(hearing), "outcome": outcome or None}
        _, err = api_post(f"/cases/{case_id}/trials/{trial_id}/hearing", payload)
        if err:
            st.error(err)
        else:
            st.success("Hearing recorded.")
            st.rerun()


@st.dialog("Apply Punishment")
def dialog_apply_punishment(case_id, trial_id, suspects):
    st.caption("Note: each person must already have a Criminal profile, or the API returns 400.")
    s_opts = {c.person_name(s.get("person")): s.get("suspect_id") for s in suspects}
    chosen = st.multiselect("Persons *", list(s_opts.keys()))
    fine = st.number_input("Fine (₹)", min_value=0, value=0)
    col1, col2 = st.columns(2)
    jail_start = col1.date_input("Jail start", value=None)
    jail_end = col2.date_input("Jail end", value=None)
    death = st.checkbox("Death penalty")
    if st.button("Apply", type="primary", disabled=not chosen):
        try:
            payload = c.build_punishment_payload(
                [s_opts[k] for k in chosen], fine=fine or None,
                jail_start=jail_start, jail_end=jail_end,
                death_penalty="Y" if death else None)
        except ValueError as e:
            st.error(str(e))
            return
        _, err = api_post(f"/cases/{case_id}/trials/{trial_id}/punishment", payload)
        if err:
            st.error(err)
        else:
            st.success("Punishment applied.")
            st.rerun()


@st.dialog("Assign Officer")
def dialog_assign_officer(case_id):
    oid = person_picker("Officer", f"off_{case_id}", role="officer")
    if st.button("Assign", type="primary", disabled=not oid):
        _, err = api_post(f"/cases/{case_id}/officers/{oid}", {})
        if err:
            st.error(err)
        else:
            st.success(f"Officer {oid} assigned.")
            st.rerun()


# ── Edit dialogs ──────────────────────────────────────────────────────────────
@st.dialog("Edit Case")
def dialog_edit_case(case_obj):
    case_id = case_obj.get("case_id")
    summary = st.text_area("Summary", value=case_obj.get("summary") or "", max_chars=255)
    crime_type = st.text_input("Crime type", value=case_obj.get("crime_type") or "")
    status = st.selectbox("Status", ["open", "on_hold", "closed"],
                          index=["open", "on_hold", "closed"].index(case_obj.get("status") or "open"))
    if st.button("Save", type="primary"):
        payload = {"summary": summary or None, "crime_type": crime_type or None, "status": status}
        _, err = api_patch(f"/cases/{case_id}", payload)
        if err:
            st.error(err)
        else:
            st.success("Case updated.")
            st.rerun()


@st.dialog("Close Case")
def dialog_close_case(case_id):
    closed = st.date_input("Closed on", value=None)
    if st.button("Close case", type="primary"):
        _, err = api_patch(f"/cases/{case_id}/close", {"closed_at": c.iso(closed)})
        if err:
            st.error(err)
        else:
            st.success("Case closed.")
            st.rerun()


@st.dialog("Update Suspect")
def dialog_update_suspect(case_id, suspect):
    sid = suspect.get("suspect_id")
    arrest = st.selectbox("Arrest status", ARREST,
                          index=ARREST.index(suspect.get("arrest_status"))
                          if suspect.get("arrest_status") in ARREST else 0)
    desc = st.text_input("Physical description", value=suspect.get("physical_description") or "")
    contact = st.text_input("Family contact", value=suspect.get("family_contact") or "")
    if st.button("Save", type="primary"):
        payload = {"arrest_status": arrest, "physical_description": desc or None,
                   "family_contact": contact or None}
        _, err = api_patch(f"/cases/{case_id}/suspects/{sid}", payload)
        if err:
            st.error(err)
        else:
            st.success("Suspect updated.")
            st.rerun()


@st.dialog("Edit Person")
def dialog_edit_person(person):
    pid = person.get("person_id")
    col1, col2, col3 = st.columns(3)
    first = col1.text_input("First name", value=person.get("first_name") or "")
    middle = col2.text_input("Middle", value=person.get("middle_name") or "")
    last = col3.text_input("Last name", value=person.get("last_name") or "")
    occupation = st.text_input("Occupation", value=person.get("occupation") or "")
    contact = st.text_input("Contact number", value=person.get("contact_number") or "")
    if st.button("Save", type="primary"):
        payload = {"first_name": first or None, "middle_name": middle or None,
                   "last_name": last or None, "occupation": occupation or None,
                   "contact_number": contact or None}
        _, err = api_patch(f"/persons/{pid}", payload)
        if err:
            st.error(err)
        else:
            st.success("Person updated.")
            st.rerun()
