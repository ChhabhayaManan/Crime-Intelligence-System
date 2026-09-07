import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from collections import Counter
from datetime import datetime
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
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

cases = cases_data.get("items", [])

statuses = Counter(c.map_status(case.get("status")) for case in cases)
open_c, hold_c, closed_c = statuses["open"], statuses["hold"], statuses["closed"]
total = len(cases)
denom = total or 1

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Cases", total)
c2.metric("Open Rate", f"{round(open_c / denom * 100)}%")
c3.metric("Hold Rate", f"{round(hold_c / denom * 100)}%")
c4.metric("Closed Rate", f"{round(closed_c / denom * 100)}%")

st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Cases by City — Hotspots")
    if hs_err:
        st.warning(hs_err)
    else:
        hotspots = hs_data.get("items", [])
        if hotspots:
            fig = px.bar(
                pd.DataFrame(hotspots).head(10), x="case_count", y="city", orientation="h",
                color_discrete_sequence=[theme.COLORS["accent"]],
                labels={"case_count": "Cases", "city": "City"},
            )
            fig.update_layout(**theme.PLOT_LAYOUT, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hotspot data.")

with col_right:
    st.subheader("Cases by Crime Type")
    crime_counts = Counter(case.get("crime_type") or "Unknown" for case in cases)
    if crime_counts:
        type_df = pd.DataFrame(crime_counts.most_common(10), columns=["Crime Type", "Count"])
        fig2 = px.bar(
            type_df, x="Count", y="Crime Type", orientation="h",
            color_discrete_sequence=[theme.COLORS["warn"]],
        )
        fig2.update_layout(**theme.PLOT_LAYOUT, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, use_container_width=True)

st.divider()
col_b, col_r = st.columns(2)

with col_b:
    st.subheader("Case Status Breakdown")
    fig3 = go.Figure(go.Pie(
        labels=["Open", "Hold", "Closed"],
        values=[open_c, hold_c, closed_c],
        marker_colors=["#22c55e", "#fbbf24", theme.COLORS["muted"]],
        hole=0.45,
    ))
    fig3.update_layout(**theme.PLOT_LAYOUT)
    st.plotly_chart(fig3, use_container_width=True)

with col_r:
    st.subheader("City Distribution")
    city_counts = Counter(case.get("city") or "Unknown" for case in cases)
    if city_counts:
        city_df = pd.DataFrame(city_counts.most_common(8), columns=["City", "Cases"])
        fig4 = px.pie(city_df, names="City", values="Cases",
                      color_discrete_sequence=px.colors.sequential.Blues_r)
        fig4.update_layout(**theme.PLOT_LAYOUT)
        st.plotly_chart(fig4, use_container_width=True)
