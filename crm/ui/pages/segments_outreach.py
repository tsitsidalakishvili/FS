import streamlit as st

from crm.ui.pages.outreach import render_outreach_page
from crm.ui.pages.segments import render_segments_tab


def render_segments_outreach_page():
    st.subheader("Segments & Outreach")
    st.caption("Build target segments, then create outreach tasks from them.")
    segments_tab, outreach_tab = st.tabs(["Segments", "Outreach"])

    with segments_tab:
        render_segments_tab()

    with outreach_tab:
        render_outreach_page()
