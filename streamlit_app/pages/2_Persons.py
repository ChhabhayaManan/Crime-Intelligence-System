import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import components as c
import theme
import forms
from utils import require_auth, api_get

PAGE_SIZE = 50

ROLE_ICON = {
    "officer": "🔵", "suspect": "🔴", "witness": "🟡",
    "victim": "🟠", "criminal": "⚫",
}

ROLE_FIELDS = [
    ("officer", "Officer", [("Rank", "rank"), ("Department", "department")]),
    ("suspect", "Suspect", [("Arrest Status", "arrest_status"),
                            ("Physical Description", "physical_description"),
                            ("Family Contact", "family_contact")]),
    ("witness", "Witness", [("Testimony", "testimony"),
                            ("Family Contact", "family_contact")]),
    ("victim", "Victim", [("Harm Details", "harm_details"),
                          ("Family Contact", "family_contact")]),
    ("criminal", "Criminal", [("Family Contact", "c_family_contact")]),
]

st.set_page_config(page_title="Persons — CIS", layout="wide")
require_auth()

st.title("Persons Registry")
_, top2 = st.columns([4, 1])
with top2:
    if st.button("➕ New person", use_container_width=True):
        forms.dialog_new_person()

col1, col2 = st.columns([3, 1])
with col1:
    search = st.text_input("Search by name", placeholder="e.g. Sharma")
with col2:
    role_filter = st.selectbox("Role", ["all", "officer", "suspect", "witness", "victim", "criminal"])

params = {"page_size": PAGE_SIZE}
if search:
    params["query"] = search
if role_filter != "all":
    params["role"] = role_filter

with st.spinner("Loading persons..."):
    raw, err = api_get("/persons", params)

if err:
    st.error(err)
    st.stop()

persons = raw.get("items", [])
total = (raw.get("meta") or {}).get("total", len(persons))
if not persons:
    st.info("No persons found.")
    st.stop()

rows = [{
    "_person_id": p.get("person_id"),
    "Name": c.person_name(p),
    "Roles": " ".join(ROLE_ICON.get(r, "⚪") + " " + r for r in p.get("roles", [])) or "—",
    "Address ID": p.get("address_id") or "—",
} for p in persons]

df = pd.DataFrame(rows)
st.caption(f"{len(df)} of {total} persons")
if total > len(df):
    st.info(f"Showing the first {len(df)}. Narrow the search to see the rest.")

selected = st.dataframe(
    df.drop(columns=["_person_id"]),
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

sel_rows = selected.selection.rows if selected.selection else []
if not sel_rows:
    st.stop()

pid = df.iloc[sel_rows[0]]["_person_id"]

st.divider()

with st.spinner("Loading profile..."):
    p, p_err = api_get(f"/persons/{pid}")
    person_cases, cases_err = api_get(f"/persons/{pid}/cases")

if p_err:
    st.error(p_err)
    st.stop()

addr = p.get("address") or {}
rd = p.get("role_details") or {}

st.subheader(c.person_name(p))

if st.button("✏️ Edit person"):
    forms.dialog_edit_person(p)

meta_parts = []
if p.get("gender"):          meta_parts.append(f"**Gender:** {c.gender_label(p['gender'])}")
if p.get("birth_date"):      meta_parts.append(f"**DOB:** {c.fmt_date(p['birth_date'])}")
if p.get("occupation"):      meta_parts.append(f"**Occupation:** {p['occupation']}")
if p.get("contact_number"):  meta_parts.append(f"**Contact:** {p['contact_number']}")
if meta_parts:
    st.markdown(" &nbsp;|&nbsp; ".join(meta_parts))

addr_str = c.fmt_addr(addr)
if addr_str != "—":
    st.markdown(f"📍 {addr_str}")

roles = p.get("roles", [])
if roles:
    st.markdown(" ".join(theme.badge(r.upper()) for r in roles), unsafe_allow_html=True)

st.divider()

role_records = [(label, rd[key], fields) for key, label, fields in ROLE_FIELDS if rd.get(key)]
person_cases = person_cases or []

tabs = st.tabs([r[0] for r in role_records] + [f"Cases ({len(person_cases)})"])

for tab, (label, data, fields) in zip(tabs, role_records):
    with tab:
        shown = False
        for title, field in fields:
            value = data.get(field)
            if not value:
                continue
            if field == "arrest_status":
                value = f"{c.arrest_icon(value)} `{str(value).upper()}`"
            st.markdown(f"**{title}:** {value}")
            shown = True
        if not shown:
            st.caption(f"No {label.lower()} details on record.")

with tabs[-1]:
    if cases_err:
        st.warning(cases_err)
    elif not person_cases:
        st.info("No cases linked to this person.")
    else:
        st.dataframe(pd.DataFrame([{
            "Reference": c.case_ref(case.get("open_date"), case.get("case_id")),
            "Crime Type": case.get("crime_type") or "—",
            "Status": c.map_status(case.get("status")),
            "Role(s)": ", ".join(case.get("roles", [])) or "—",
            "Opened": c.fmt_date(case.get("open_date")),
        } for case in person_cases]), use_container_width=True, hide_index=True)
