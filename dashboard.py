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

with st.container(horizontal=True, vertical_alignment="center", gap="small"):
    st.markdown(
        "<div style='font-size: clamp(1.3rem, 4vw, 1.9rem); font-weight: 700; line-height: 1.2; margin: 0;'>🌊 Tisza – Tiszadorogma</div>",
        unsafe_allow_html=True,
    )
    version = st.segmented_control(
        "Nézet",
        options=["📱", "🖥️"],
        default="📱",
        label_visibility="collapsed",
    )

if version == "🖥️":
    dashboard_v1.render(show_title=False)
else:
    dashboard_v2.render(show_title=False)
