import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime
import streamlit as st
import pandas as pd
import components as c
import theme
import forms
from utils import require_auth, api_get

st.set_page_config(page_title="Dashboard — CIS", layout="wide")
require_auth()

# Topbar
st.markdown(
    theme.topbar(st.session_state.get("username_display", "—"),
                 datetime.now().strftime("%d %b %Y %H:%M").upper()),
    unsafe_allow_html=True,
)

# ── Load cases ────────────────────────────────────────────────────────────────
with st.spinner("Loading cases..."):
    cases_data, cases_err = api_get("/cases", {"page_size": 200, "sort": "-open_date"})
    hs_data, _ = api_get("/analytics/hotspots")
if cases_err:
    st.error(cases_err)
    st.stop()
cases = cases_data.get("items", [])

# Stat cards
open_c = sum(1 for x in cases if c.map_status(x.get("status")) == "open")
hold_c = sum(1 for x in cases if c.map_status(x.get("status")) == "hold")
closed_c = sum(1 for x in cases if c.map_status(x.get("status")) == "closed")
s1, s2, s3, s4 = st.columns([1, 1, 1, 1])
s1.markdown(theme.stat_card("OPEN CASES", open_c, "#1860c4"), unsafe_allow_html=True)
s2.markdown(theme.stat_card("ON HOLD", hold_c, "#c47e0a"), unsafe_allow_html=True)
s3.markdown(theme.stat_card("CLOSED", closed_c, "#264a38"), unsafe_allow_html=True)
with s4:
    st.write("")
    if st.button("➕ New Case", use_container_width=True, type="primary"):
        forms.dialog_new_case()

st.divider()

# ── Filters ───────────────────────────────────────────────────────────────────
f1, f2, f3 = st.columns([2, 1, 1])
search = f1.text_input("Crime type", placeholder="e.g. Burglary")
status_filter = f2.selectbox("Status", ["all", "open", "hold", "closed"])
city_filter = f3.text_input("City", placeholder="e.g. Mumbai")


def _visible(x):
    if search and search.lower() not in (x.get("crime_type") or "").lower():
        return False
    if city_filter and city_filter.lower() not in (x.get("city") or "").lower():
        return False
    if status_filter != "all" and c.map_status(x.get("status")) != status_filter:
        return False
    return True


visible = [x for x in cases if _visible(x)]

rows = [{
    "_case_id": x.get("case_id"),
    "Reference": c.case_ref(x.get("open_date"), x.get("case_id")),
    "Crime Type": x.get("crime_type", "—"),
    "City": x.get("city", "—"),
    "Status": c.status_icon(c.map_status(x.get("status"))) + " " + c.map_status(x.get("status")),
    "Opened": c.fmt_date(x.get("open_date")),
} for x in visible]

st.caption(f"{len(rows)} records")
if not rows:
    st.info("No cases match the filters.")
    st.stop()

df = pd.DataFrame(rows)
selected = st.dataframe(
    df.drop(columns=["_case_id"]), use_container_width=True, hide_index=True,
    on_select="rerun", selection_mode="single-row",
)
sel_rows = selected.selection.rows if selected.selection else []
if not sel_rows:
    st.stop()
case_id = int(df.iloc[sel_rows[0]]["_case_id"])

# ── Case detail (3-column) ────────────────────────────────────────────────────
st.divider()
with st.spinner("Loading case..."):
    det, derr = api_get(f"/cases/{case_id}/details",
                        {"include": "evidence,witnesses,suspects,victims,trials,testimonies"})
if derr:
    st.error(derr)
    st.stop()

case_obj = det.get("case", {})
suspects = det.get("suspects", [])
evidence = det.get("evidence", [])
witnesses = det.get("witnesses", [])
victims = det.get("victims", [])
trials = det.get("trials", [])
testimonies = det.get("testimonies", [])

status = c.map_status(case_obj.get("status"))
ref = c.case_ref(case_obj.get("open_date"), case_obj.get("case_id"))
wanted = sum(1 for s in suspects if (s.get("arrest_status") or "").lower() == "wanted")

h1, h2 = st.columns([3, 1])
with h1:
    st.subheader(f"{ref} — {case_obj.get('crime_type', '—')}")
    chips = theme.badge(status.upper(), status)
    if wanted:
        chips += " " + theme.badge(f"{wanted} WANTED", "danger")
    st.markdown(chips, unsafe_allow_html=True)
    st.caption(
        f"City: {(case_obj.get('location') or {}).get('city', '—')}  ·  "
        f"Crime: {c.fmt_date(case_obj.get('crime_date'))}  ·  "
        f"Opened: {c.fmt_date(case_obj.get('open_date'))}"
    )
with h2:
    if st.button("✏️ Edit", use_container_width=True):
        forms.dialog_edit_case(case_obj)
    if status != "closed" and st.button("⛔ Close case", use_container_width=True):
        forms.dialog_close_case(case_id)

if case_obj.get("summary"):
    st.info(case_obj["summary"])

# Pre-load trial details
trial_details = {}
for tr in trials:
    tid = tr.get("trial_id") or tr.get("trial_number")
    if tid:
        td, _ = api_get(f"/cases/{case_id}/trials/{tid}")
        if td:
            trial_details[tid] = td

col_people, col_evi, col_time = st.columns([28, 36, 36])

# People column
with col_people:
    st.markdown(theme.panel_header("PEOPLE"), unsafe_allow_html=True)
    tab_s, tab_w, tab_v = st.tabs([f"Suspects {len(suspects)}",
                                   f"Witnesses {len(witnesses)}",
                                   f"Victims {len(victims)}"])
    with tab_s:
        if st.button("＋ Add suspect", key="add_susp"):
            forms.dialog_add_suspect(case_id, evidence)
        for s in suspects:
            with st.container(border=True):
                st.markdown(f"{c.arrest_icon(s.get('arrest_status'))} **{c.person_name(s.get('person'))}** "
                            f"— `{s.get('arrest_status', '—')}`")
                if s.get("physical_description"):
                    st.caption(s["physical_description"])
                if st.button("Update status", key=f"upd_{s.get('suspect_id')}"):
                    forms.dialog_update_suspect(case_id, s)
    with tab_w:
        if st.button("＋ Add witness", key="add_wit"):
            forms.dialog_add_witness(case_id)
        for w in witnesses:
            with st.container(border=True):
                st.markdown(f"**{c.person_name(w.get('person'))}**")
                if w.get("statement"):
                    st.caption(f"\"{w['statement']}\"")
        if witnesses and st.button("＋ Record testimony", key="add_test"):
            forms.dialog_record_testimony(case_id, witnesses, suspects)
    with tab_v:
        if st.button("＋ Add victim", key="add_vic"):
            forms.dialog_add_victim(case_id)
        for v in victims:
            with st.container(border=True):
                st.markdown(f"**{c.person_name(v.get('person'))}**")
                if v.get("harm_details"):
                    st.caption(v["harm_details"])

# Evidence column
with col_evi:
    st.markdown(theme.panel_header(f"EVIDENCE {len(evidence)}"), unsafe_allow_html=True)
    if st.button("＋ Add evidence", key="add_evi"):
        forms.dialog_add_evidence(case_id)
    for ev in evidence:
        with st.container(border=True):
            tag = f" 📎 {ev.get('file_content_type')}" if ev.get("file_key") else ""
            st.markdown(f"`EV-{ev.get('evidence_id')}`{tag}")
            st.caption(ev.get("description") or "No description")
            st.caption(f"Collected {c.fmt_date(ev.get('collection_date'))}")

# Timeline + Trial column
with col_time:
    st.markdown(theme.panel_header("CASE TIMELINE"), unsafe_allow_html=True)
    st.markdown(f"- **Case opened** — {c.fmt_date(case_obj.get('open_date'))}")
    st.markdown(f"- **{len(evidence)}** evidence item(s) collected")
    st.markdown(f"- **{len(suspects)}** suspect(s) identified")
    st.markdown(f"- Trial proceedings — {'filed' if trials else 'pending'}")
    st.markdown(theme.panel_header(f"TRIAL {len(trials)}"), unsafe_allow_html=True)
    if st.button("＋ Add trial", key="add_trial"):
        forms.dialog_add_trial(case_id)
    for tr in trials:
        tid = tr.get("trial_id") or tr.get("trial_number")
        td = trial_details.get(tid, {})
        with st.container(border=True):
            st.markdown(f"**Trial #{tr.get('trial_number')}** — {tr.get('court_level', '—')}")
            st.caption(f"Judge: {tr.get('judge_id', '—')}  ·  Hearing: {c.fmt_date(tr.get('hearing_date'))}")
            cta1, cta2 = st.columns(2)
            if cta1.button("＋ Hearing", key=f"hear_{tid}"):
                forms.dialog_add_hearing(case_id, tid)
            if cta2.button("＋ Punishment", key=f"pun_{tid}"):
                forms.dialog_apply_punishment(case_id, tid, suspects)
            for pu in td.get("punishments", []):
                st.caption(f"Person {pu.get('criminal_person_id')} · fine ₹{pu.get('fine') or 0} · "
                           f"{'DEATH' if pu.get('death_penalty') == 'Y' else ''}")
    st.markdown(theme.panel_header("OFFICERS"), unsafe_allow_html=True)
    off_ids = case_obj.get("assigned_officer_ids", [])
    st.caption(", ".join(f"OFF-{o}" for o in off_ids) if off_ids else "None assigned")
    if st.button("＋ Assign officer", key="add_off"):
        forms.dialog_assign_officer(case_id)
