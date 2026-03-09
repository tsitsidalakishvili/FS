from __future__ import annotations

import streamlit as st

from crm.ui.pages.deliberation import render_deliberation
from crm.ui.shell import (
    apply_global_styles,
    ensure_supporter_access,
    handle_special_entrypoints,
)


st.set_page_config(page_title="Freedom Square CRM", layout="wide")
apply_global_styles()
if handle_special_entrypoints():
    st.stop()
if not ensure_supporter_access("Deliberation"):
    st.stop()

render_deliberation(public_only=False)
