import smtplib
from email.message import EmailMessage

import streamlit as st

from crm.config import (
    FEEDBACK_EMAIL_FROM,
    FEEDBACK_EMAIL_TO,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USER,
)


def _parse_int(value, default):
    try:
        return int(value)
    except Exception:
        return default


def feedback_email_configured():
    return bool(FEEDBACK_EMAIL_TO and SMTP_HOST)


def send_feedback_email(name, email, message, page=None):
    if not feedback_email_configured():
        return False, "Email feedback is not configured."
    from_email = FEEDBACK_EMAIL_FROM or FEEDBACK_EMAIL_TO
    msg = EmailMessage()
    msg["Subject"] = f"Feedback ({page or 'app'})"
    msg["From"] = from_email
    msg["To"] = FEEDBACK_EMAIL_TO
    if email:
        msg["Reply-To"] = email

    body_lines = [
        f"Name: {name or 'Anonymous'}",
        f"Email: {email or 'Not provided'}",
        f"Page: {page or 'Unknown'}",
        "",
        message,
    ]
    msg.set_content("\n".join(body_lines))

    port = _parse_int(SMTP_PORT, 587)
    try:
        with smtplib.SMTP(SMTP_HOST, port, timeout=20) as server:
            server.ehlo()
            if SMTP_USE_TLS:
                server.starttls()
                server.ehlo()
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASSWORD or "")
            server.send_message(msg)
        return True, None
    except Exception as exc:
        return False, str(exc)


def render_feedback_widget(page_label="App"):
    with st.sidebar.expander("Feedback", expanded=False):
        st.caption("Send feedback directly to the team.")
        if not feedback_email_configured():
            st.info("Email feedback is not configured yet.")
            st.caption("Set `FEEDBACK_EMAIL_TO` and SMTP settings in `.env` or Streamlit secrets.")
            return
        with st.form("feedback_form", clear_on_submit=True):
            name = st.text_input("Name (optional)", key="feedback_name")
            email = st.text_input("Email (optional)", key="feedback_email")
            message = st.text_area("Your feedback", key="feedback_message")
            submitted = st.form_submit_button("Send feedback")
        if submitted:
            if not message.strip():
                st.warning("Please enter a message.")
            else:
                ok, error = send_feedback_email(
                    name.strip(),
                    email.strip(),
                    message.strip(),
                    page=page_label,
                )
                if ok:
                    st.success("Thanks! Your feedback was sent.")
                else:
                    st.error(f"Could not send feedback: {error}")
