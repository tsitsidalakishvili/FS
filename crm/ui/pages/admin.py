import streamlit as st

import crm.db.neo4j as neo4j_db
from crm.clients.deliberation import delib_api_get
from crm.config import (
    DELIBERATION_API_URL,
    FEEDBACK_EMAIL_FROM,
    FEEDBACK_EMAIL_TO,
    PUBLIC_ONLY,
    SUPPORTER_ACCESS_CODE,
    WHATSAPP_GROUP_WEBHOOK_URL,
)
from crm.services.feedback import feedback_email_configured


def render_admin_page():
    st.subheader("Admin")
    st.caption("Configuration and system status.")

    st.markdown("### System status")
    db_status = "Connected" if neo4j_db.driver is not None else "Not connected"
    st.write(f"**Neo4j**: {db_status}")

    delib_ok = delib_api_get("/conversations", show_error=False)
    delib_status = "Online" if delib_ok is not None else "Offline / not configured"
    st.write(f"**Deliberation API**: {delib_status}")
    st.caption(f"API URL: {DELIBERATION_API_URL}")

    st.markdown("### Access mode")
    st.write(f"**Public only**: {'Yes' if PUBLIC_ONLY else 'No'}")
    st.write(f"**Supporter access code set**: {'Yes' if SUPPORTER_ACCESS_CODE else 'No'}")

    st.markdown("### Feedback email")
    st.write(f"**Configured**: {'Yes' if feedback_email_configured() else 'No'}")
    st.write(f"**From**: {FEEDBACK_EMAIL_FROM or 'Not set'}")
    st.write(f"**To**: {FEEDBACK_EMAIL_TO or 'Not set'}")

    st.markdown("### WhatsApp")
    st.write(f"**Group webhook configured**: {'Yes' if WHATSAPP_GROUP_WEBHOOK_URL else 'No'}")
