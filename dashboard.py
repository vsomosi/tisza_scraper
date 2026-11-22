from __future__ import annotations

import streamlit as st
import dashboard_v1
import dashboard_v2

st.set_page_config(
    page_title="Tiszadorogma Dashboard",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

version = st.segmented_control(
    "Nézet verziója",
    options=["📱 v2 (Mobilbarát)", "🖥️ v1 (Klasszikus)"],
    default="📱 v2 (Mobilbarát)",
    label_visibility="collapsed",
)

if version == "🖥️ v1 (Klasszikus)":
    dashboard_v1.render()
else:
    dashboard_v2.render()
