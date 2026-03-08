from __future__ import annotations

import streamlit as st

from crm.ui.pages.due_diligence import render_due_diligence_page
from crm.ui.shell import (
    apply_global_styles,
    ensure_db_connection,
    ensure_supporter_access,
    handle_special_entrypoints,
)


st.set_page_config(page_title="Freedom Square CRM", layout="wide")
apply_global_styles()
if handle_special_entrypoints():
    st.stop()
if not ensure_supporter_access("Due Diligence"):
    st.stop()
if not ensure_db_connection():
    st.stop()

render_due_diligence_page()
