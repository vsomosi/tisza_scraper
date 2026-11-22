from __future__ import annotations

import streamlit as st
import dashboard_v2

st.set_page_config(
    page_title="Tiszadorogma Vízállás",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

dashboard_v2.render(show_title=True)
