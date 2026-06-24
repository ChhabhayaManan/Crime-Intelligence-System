import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import components as c
import theme
from utils import require_auth, api_get

st.set_page_config(page_title="Analytics — CIS", layout="wide")
require_auth()

st.markdown(theme.topbar(st.session_state.get("username_display", "—"),
            datetime.now().strftime("%d %b %Y %H:%M").upper()), unsafe_allow_html=True)

st.title("Crime Analytics")
st.caption("INTELLIGENCE REPORT")

with st.spinner("Loading..."):
    hs_data, hs_err = api_get("/analytics/hotspots")
    cases_data, cases_err = api_get("/cases", {"page_size": 200, "sort": "-open_date"})

if cases_err:
    st.error(cases_err)
    st.stop()

# CaseListItem: case_id, open_date, crime_date, crime_type, status, city
cases = cases_data.get("items", [])

statuses = [c.map_status(case.get("status")) for case in cases]
open_c   = statuses.count("open")
hold_c   = statuses.count("hold")
closed_c = statuses.count("closed")
total    = len(cases) or 1

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Cases", total)
c2.metric("Open Rate", f"{round(open_c/total*100)}%")
c3.metric("Hold Rate", f"{round(hold_c/total*100)}%")
c4.metric("Closed Rate", f"{round(closed_c/total*100)}%")

st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Cases by City — Hotspots")
    if hs_err:
        st.warning(hs_err)
    else:
        # CrimeHotspotResponse: { items: [{city, case_count}] }
        hotspots = hs_data.get("items", [])
        if hotspots:
            hs_df = pd.DataFrame(hotspots)
            fig = px.bar(
                hs_df.head(10), x="case_count", y="city", orientation="h",
                color_discrete_sequence=["#1860c4"],
                labels={"case_count": "Cases", "city": "City"},
            )
            fig.update_layout(
                paper_bgcolor="#0c1220", plot_bgcolor="#0c1220",
                font_color="#dce8f5", margin=dict(l=0, r=10, t=0, b=0),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hotspot data.")

with col_right:
    st.subheader("Cases by Crime Type")
    crime_map = {}
    for case in cases:
        t = case.get("crime_type") or "Unknown"
        crime_map[t] = crime_map.get(t, 0) + 1
    if crime_map:
        type_df = pd.DataFrame(
            sorted(crime_map.items(), key=lambda x: x[1], reverse=True),
            columns=["Crime Type", "Count"]
        ).head(10)
        fig2 = px.bar(
            type_df, x="Count", y="Crime Type", orientation="h",
            color_discrete_sequence=["#c47e0a"],
        )
        fig2.update_layout(
            paper_bgcolor="#0c1220", plot_bgcolor="#0c1220",
            font_color="#dce8f5", margin=dict(l=0, r=10, t=0, b=0),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig2, use_container_width=True)

st.divider()
col_b, col_r = st.columns(2)

with col_b:
    st.subheader("Case Status Breakdown")
    fig3 = go.Figure(go.Pie(
        labels=["Open", "Hold", "Closed"],
        values=[open_c, hold_c, closed_c],
        marker_colors=["#22c55e", "#fbbf24", "#6898b8"],
        hole=0.45,
    ))
    fig3.update_layout(
        paper_bgcolor="#0c1220", font_color="#dce8f5",
        margin=dict(l=0, r=0, t=0, b=0),
    )
    st.plotly_chart(fig3, use_container_width=True)

with col_r:
    st.subheader("City Distribution")
    city_map = {}
    for case in cases:
        city = case.get("city") or "Unknown"
        city_map[city] = city_map.get(city, 0) + 1
    if city_map:
        city_df = pd.DataFrame(
            sorted(city_map.items(), key=lambda x: x[1], reverse=True)[:8],
            columns=["City", "Cases"]
        )
        fig4 = px.pie(city_df, names="City", values="Cases",
                      color_discrete_sequence=px.colors.sequential.Blues_r)
        fig4.update_layout(
            paper_bgcolor="#0c1220", font_color="#dce8f5",
            margin=dict(l=0, r=0, t=0, b=0),
        )
        st.plotly_chart(fig4, use_container_width=True)
