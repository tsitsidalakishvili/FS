from __future__ import annotations

import streamlit as st

from crm.ui.shell import (
    apply_global_styles,
    ensure_db_connection,
    ensure_supporter_access,
    handle_special_entrypoints,
)


st.set_page_config(page_title="Freedom Square CRM", layout="wide")
apply_global_styles()
st.title("Freedom Square CRM")

if handle_special_entrypoints():
    st.stop()

if not ensure_supporter_access("Home"):
    st.stop()
if not ensure_db_connection():
    st.stop()

st.markdown("### Home")
st.write(
    "Use the sidebar **Pages** navigation to open Dashboard, People, Tasks, Outreach, "
    "Map, Events, Due Diligence, Data, Admin, and Deliberation."
)
st.caption(
    "This app now uses native Streamlit multipage routing. Query links for survey, "
    "deliberation, and event registration are still supported."
)
