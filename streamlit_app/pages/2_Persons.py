import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import components as c
import theme
import forms
from utils import require_auth, api_get

st.set_page_config(page_title="Persons — CIS", layout="wide")
require_auth()


# ── List / Filters ────────────────────────────────────────────────────────────
st.title("Persons Registry")
top1, top2 = st.columns([4, 1])
with top2:
    if st.button("➕ New person", use_container_width=True):
        forms.dialog_new_person()

col1, col2 = st.columns([3, 1])
with col1:
    search = st.text_input("Search by name", placeholder="e.g. Sharma")
with col2:
    role_filter = st.selectbox("Role", ["all", "officer", "suspect", "witness", "victim", "criminal"])

params = {"page_size": 50}
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
if not persons:
    st.info("No persons found.")
    st.stop()

ROLE_ICON = {
    "officer": "🔵", "suspect": "🔴", "witness": "🟡",
    "victim": "🟠", "criminal": "⚫",
}

rows = [{
    "_person_id": p.get("person_id"),
    "Name": c.person_name(p),
    "Roles": " ".join(ROLE_ICON.get(r, "⚪") + " " + r for r in p.get("roles", [])) or "—",
    "Address ID": p.get("address_id", "—"),
} for p in persons]

df = pd.DataFrame(rows)
st.caption(f"{len(df)} persons found")

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

# ── Person Detail ─────────────────────────────────────────────────────────────
st.divider()

with st.spinner("Loading profile..."):
    p_data, p_err = api_get(f"/persons/{pid}")
    cases_data, _ = api_get(f"/persons/{pid}/cases")

if p_err:
    st.error(p_err)
    st.stop()

p    = p_data
addr = p.get("address") or {}
rd   = p.get("role_details") or {}

# Header
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
if addr_str and addr_str != "—":
    st.markdown(f"📍 {addr_str}")

roles = p.get("roles", [])
if roles:
    st.markdown(" ".join(theme.badge(r.upper()) for r in roles), unsafe_allow_html=True)

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
role_records = []
if rd.get("officer"):   role_records.append(("Officer",  rd["officer"]))
if rd.get("suspect"):   role_records.append(("Suspect",  rd["suspect"]))
if rd.get("witness"):   role_records.append(("Witness",  rd["witness"]))
if rd.get("victim"):    role_records.append(("Victim",   rd["victim"]))
if rd.get("criminal"):  role_records.append(("Criminal", rd["criminal"]))

person_cases: list = []
if cases_data is not None:
    person_cases = cases_data if isinstance(cases_data, list) else cases_data.get("items", [])

tab_labels = [r[0] for r in role_records] + [f"Cases ({len(person_cases)})"]
tabs = st.tabs(tab_labels)

for i, (label, data) in enumerate(role_records):
    with tabs[i]:
        if label == "Officer":
            c1, c2 = st.columns(2)
            c1.metric("Rank", data.get("rank") or "—")
            c2.metric("Department", data.get("department") or "—")

        elif label == "Suspect":
            a_status = str(data.get("arrest_status") or "—").upper()
            badge_icon = {"WANTED": "🔴", "ARRESTED": "🟠", "RELEASED": "🟢"}.get(a_status, "⚪")
            st.markdown(f"**Arrest Status:** {badge_icon} `{a_status}`")
            if data.get("physical_description"):
                st.markdown(f"**Physical Description:** {data['physical_description']}")
            if data.get("family_contact"):
                st.markdown(f"**Family Contact:** {data['family_contact']}")

        elif label == "Witness":
            if data.get("testimony"):
                st.markdown(f"**Testimony:** {data['testimony']}")
            else:
                st.caption("No testimony on record.")
            if data.get("family_contact"):
                st.markdown(f"**Family Contact:** {data['family_contact']}")

        elif label == "Victim":
            if data.get("harm_details"):
                st.markdown(f"**Harm Details:** {data['harm_details']}")
            else:
                st.caption("No harm details on record.")
            if data.get("family_contact"):
                st.markdown(f"**Family Contact:** {data['family_contact']}")

        elif label == "Criminal":
            if data.get("c_family_contact"):
                st.markdown(f"**Family Contact:** {data['c_family_contact']}")
            else:
                st.caption("No criminal profile details.")

# Cases tab — uses /persons/{pid}/cases response:
# { case_id, open_date, crime_type, status (raw), roles (list) }
with tabs[-1]:
    if cases_data is None:
        st.warning("Cases endpoint unavailable.")
    elif not person_cases:
        st.info("No cases linked to this person.")
    else:
        crows = []
        for case in person_cases:
            crows.append({
                "Reference": f"CIS/{str(case.get('open_date',''))[:4]}/{str(case.get('case_id','')).zfill(4)}",
                "Crime Type": case.get("crime_type", "—"),
                "Status": c.map_status(case.get("status", "")),
                "Role(s)": ", ".join(case.get("roles", [])) or "—",
                "Opened": c.fmt_date(case.get("open_date")),
            })
        st.dataframe(pd.DataFrame(crows), use_container_width=True, hide_index=True)
