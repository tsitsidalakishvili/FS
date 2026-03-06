import json
import os

import streamlit as st

from crm.clients.deliberation import delib_api_get, render_delib_api_unavailable

FORMS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "forms")
)


def _safe_conversations():
    conversations = delib_api_get("/conversations", show_error=False)
    return conversations if conversations is not None else None


def _load_survey_templates():
    templates = []
    if not os.path.isdir(FORMS_DIR):
        return templates
    for name in os.listdir(FORMS_DIR):
        if not name.lower().endswith(".json"):
            continue
        path = os.path.join(FORMS_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            continue
        template_id = data.get("id") or os.path.splitext(name)[0]
        data["_id"] = str(template_id)
        data["_source"] = path
        templates.append(data)
    return templates


def _filter_templates(templates, kind):
    filtered = []
    for template in templates:
        audience = template.get("audience") or []
        if not audience or kind in audience:
            filtered.append(template)
    return filtered


def _build_message(template, link):
    message = template.get("message_template")
    if not message:
        return f"{template.get('title','Survey')}\n\nPlease fill the form:\n{link}"
    try:
        return message.format(link=link, title=template.get("title", "Survey"))
    except Exception:
        return message


def _render_field(field, key_prefix):
    field_id = field.get("id") or "field"
    label = field.get("label") or field_id
    field_type = (field.get("type") or "text").lower()
    options = field.get("options") or []
    key = f"{key_prefix}_{field_id}"

    if field_type == "textarea":
        return st.text_area(label, key=key, height=90)
    if field_type == "select":
        return st.selectbox(label, options=options, key=key)
    if field_type == "multiselect":
        return st.multiselect(label, options=options, default=[], key=key)
    if field_type == "checkbox":
        return st.checkbox(label, key=key)
    if field_type == "radio":
        return st.radio(label, options=options, key=key)
    if field_type == "number":
        return st.number_input(label, key=key)
    return st.text_input(label, key=key)


def render_survey_block(kind):
    templates = _filter_templates(_load_survey_templates(), kind)
    if not templates:
        st.info("No survey templates found in crm/forms.")
        return
    options = {t.get("title", t["_id"]): t for t in templates}
    selected = st.selectbox(
        "Survey template",
        options=[""] + list(options.keys()),
        key=f"survey_template_{kind}",
        help="Templates are loaded from crm/forms/*.json.",
    )
    if not selected:
        return
    template = options[selected]
    link = f"<APP_URL>?survey={template['_id']}"
    st.text_input(
        "Shareable link",
        value=link,
        key=f"survey_link_{kind}",
        help="Replace <APP_URL> with your Streamlit app URL.",
    )
    st.text_area(
        "Message to send",
        value=_build_message(template, link),
        height=120,
        key=f"survey_message_{kind}",
    )
    st.markdown("**Preview**")
    for section in template.get("sections", []):
        st.markdown(f"- {section.get('title','Section')}")


def render_survey_page(survey_id):
    templates = _load_survey_templates()
    template = next((t for t in templates if t.get("_id") == survey_id), None)
    if template is None:
        st.error("Survey template not found.")
        return
    st.title(template.get("title", "Survey"))
    if template.get("description"):
        st.caption(template["description"])
    st.info("This is a preview form. Responses are not stored yet.")

    with st.form(f"survey_form_{template['_id']}"):
        responses = {}
        for section in template.get("sections", []):
            st.markdown(f"### {section.get('title', 'Section')}")
            for field in section.get("fields", []):
                responses[field.get("id") or field.get("label")] = _render_field(
                    field, template["_id"]
                )
        submitted = st.form_submit_button("Submit")

    if submitted:
        st.success("Thanks! This is a preview form — responses are not stored yet.")
        st.json(responses)


def render_questionnaire_block(kind, show_expander=True):
    label = "Supporter" if kind == "supporter" else "Member"
    def _render_content():
        survey_tab, delib_tab = st.tabs(["Survey form", "Deliberation"])

        with survey_tab:
            render_survey_block(kind)

        with delib_tab:
            st.caption(
                f"Send a deliberation link to {label.lower()}s so they can vote and comment."
            )
            conversations = _safe_conversations()
            if conversations is None:
                render_delib_api_unavailable()
                return
            if not conversations:
                st.info(
                    "Create a deliberation conversation first (Deliberation → Configure)."
                )
                return

            convo_options = {c["topic"]: c["id"] for c in conversations}
            selected_topic = st.selectbox(
                "Conversation",
                options=[""] + list(convo_options.keys()),
                key=f"questionnaire_convo_{kind}",
                help="Pick which deliberation conversation to send.",
            )
            if not selected_topic:
                st.caption("Select a conversation to generate the link.")
                return

            convo_id = convo_options[selected_topic]
            public_link = (
                f"<APP_URL>?questionnaire=deliberation&conversation_id={convo_id}"
            )
            admin_link = (
                f"<APP_URL>?questionnaire=deliberation_admin&conversation_id={convo_id}"
            )

            st.text_input(
                "Participant link",
                value=public_link,
                key=f"questionnaire_link_public_{kind}",
                help="Replace <APP_URL> with your Streamlit app URL.",
            )
            st.text_input(
                "Admin preview link",
                value=admin_link,
                key=f"questionnaire_link_admin_{kind}",
                help="Internal link with Configure/Moderate/Reports tabs.",
            )
            message = (
                f"Freedom Square questionnaire ({label})\n\n"
                "Please vote and comment using this link:\n"
                + public_link
            )
            st.text_area(
                "Message to send",
                value=message,
                height=120,
                key=f"questionnaire_message_{kind}",
            )

            comments = delib_api_get(
                f"/conversations/{convo_id}/comments?status=approved", show_error=False
            ) or []
            st.markdown("**Preview**")
            st.markdown(f"**{selected_topic}**")
            if comments:
                for comment in comments[:5]:
                    st.markdown(f"- {comment.get('text','')}")
            else:
                st.caption(
                    "No approved comments yet — the link will show an empty vote list."
                )

    if show_expander:
        with st.expander("Questionnaire templates (shareable)", expanded=False):
            _render_content()
    else:
        _render_content()
