import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import quote_plus, urlencode

from crm.config import FEEDBACK_EMAIL_TO, get_config


def _link_button(label: str, url: str) -> None:
    if not url:
        return
    try:
        st.link_button(label, url, use_container_width=True)
    except Exception:
        st.markdown(f"[{label}]({url})")


def _build_gmail_compose_url(*, to_email: str, subject: str, body: str) -> str:
    params = {
        "view": "cm",
        "fs": "1",
        "su": subject,
        "body": body,
    }
    to_value = str(to_email or "").strip()
    if to_value:
        params["to"] = to_value
    return "https://mail.google.com/mail/?" + urlencode(params, quote_via=quote_plus)


def _render_workflow_buttons() -> None:
    st.markdown("### Workflow steps (icons + buttons)")
    steps = [
        {
            "id": "crm",
            "label": "1) CRM Context",
            "icon": "👤",
            "detail": "Starts when organizer opens DD from a profile/task/event context.",
            "timing": "When DD tab opens",
        },
        {
            "id": "resolve",
            "label": "2) Entity Resolution",
            "icon": "🧩",
            "detail": "Maps person/company to canonical graph ID and avoids duplicate nodes.",
            "timing": "Before enrichment or risk analysis",
        },
        {
            "id": "enrich",
            "label": "3) Enrichment",
            "icon": "🔎",
            "detail": "Pulls Wikidata/OpenSanctions/News and stores source-linked entities and edges.",
            "timing": "On analyst action",
        },
        {
            "id": "weekly",
            "label": "4) Weekly Monitoring",
            "icon": "🗓️",
            "detail": "Refreshes recent news and creates MENTIONED_IN links for tracked entities.",
            "timing": "Scheduled weekly job",
        },
        {
            "id": "risk",
            "label": "5) Risk View",
            "icon": "⚠️",
            "detail": "Runs network queries (including 2-hop risky neighbors) over current graph state.",
            "timing": "When analyst opens Risk view",
        },
        {
            "id": "report",
            "label": "6) Report & Actions",
            "icon": "📄",
            "detail": "Generates evidence-backed report and drives CRM follow-up actions.",
            "timing": "When analyst exports report",
        },
    ]

    selected_id = st.session_state.get("dd_workflow_selected_step")
    for i in range(0, len(steps), 3):
        cols = st.columns(3)
        for col, step in zip(cols, steps[i : i + 3]):
            with col:
                if st.button(
                    f"{step['icon']} {step['label']}",
                    key=f"dd_step_btn_{step['id']}",
                    use_container_width=True,
                ):
                    st.session_state["dd_workflow_selected_step"] = step["id"]
                    selected_id = step["id"]

    selected = next((step for step in steps if step["id"] == selected_id), steps[0])
    st.info(
        f"{selected['icon']} **{selected['label']}**\n\n"
        f"- **When:** {selected['timing']}\n"
        f"- **What happens:** {selected['detail']}"
    )


def render_due_diligence_page():
    st.subheader("Due Diligence")
    how_it_works_tab, actual_app_tab = st.tabs(["How it works", "Actual app"])

    with how_it_works_tab:
        st.markdown("### Workflow architecture")
        dot = """
        digraph DDWorkflow {
          rankdir=LR;
          splines=true;
          node [shape=box, style="rounded,filled", fillcolor="#F4F8FB", color="#2E5B7A", fontname="Helvetica"];
          edge [color="#4A6A85", fontname="Helvetica", fontsize=10];

          CRMContext [label="CRM Context\\n(Profile / Task / Event)"];
          EntityResolution [label="Entity Resolution\\n(Person/Company ID mapping)"];
          Enrichment [label="On-demand Enrichment\\nWikidata / OpenSanctions / News"];
          WeeklyMonitor [label="Weekly Monitoring\\nScheduled news refresh"];
          GraphStore [label="Neo4j Graph\\nNodes + edges with\\nsource + ingested_at"];
          RiskView [label="Risk View\\n2-hop risky neighbors"];
          Report [label="PDF Report\\nEvidence-backed output"];
          ActionBacklog [label="CRM Actions\\nFollow-up tasks / escalation"];

          CRMContext -> EntityResolution [label="when DD tab opens"];
          EntityResolution -> Enrichment [label="analyst triggers checks"];
          EntityResolution -> GraphStore [label="if entity exists"];
          Enrichment -> GraphStore [label="new entities + links"];
          WeeklyMonitor -> GraphStore [label="weekly job\\nadds MENTIONED_IN"];
          GraphStore -> RiskView [label="query time"];
          RiskView -> Report [label="when exporting report"];
          Report -> ActionBacklog [label="decision + next actions"];
        }
        """
        try:
            st.graphviz_chart(dot)
        except Exception:
            st.code(dot, language="dot")

        _render_workflow_buttons()

        st.markdown("### Phase 1 implementation status")
        status_cols = st.columns(3)
        with status_cols[0]:
            st.button(
                "✅ Weekly links ready",
                key="dd_phase1_weekly",
                use_container_width=True,
                disabled=True,
            )
        with status_cols[1]:
            st.button(
                "✅ Fulltext search ready",
                key="dd_phase1_search",
                use_container_width=True,
                disabled=True,
            )
        with status_cols[2]:
            st.button(
                "✅ Ingestion metadata ready",
                key="dd_phase1_metadata",
                use_container_width=True,
                disabled=True,
            )

    with actual_app_tab:
        st.markdown("### Actual app")
        st.write(
            "Use this tab to access the working Due Diligence app and run live checks. "
            "Case workflow (Phase 2) will build on top of this foundation."
        )

        app_url = (
            str(get_config("DUE_DILIGENCE_APP_URL") or "").strip()
            or str(get_config("DD_APP_URL") or "").strip()
        )
        if app_url:
            st.success("External Due Diligence app is configured.")
            st.text_input("Configured app URL", value=app_url, key="dd_app_url_preview")
            action_cols = st.columns(3)
            with action_cols[0]:
                _link_button("🚀 Open DD app", app_url)
            with action_cols[1]:
                if st.button("🖼️ Toggle embed", key="dd_embed_toggle", use_container_width=True):
                    st.session_state["dd_embed_external_app"] = not bool(
                        st.session_state.get("dd_embed_external_app")
                    )
            with action_cols[2]:
                to_email = st.text_input(
                    "Gmail to",
                    value=str(FEEDBACK_EMAIL_TO or "").strip(),
                    key="dd_gmail_to",
                    help="Optional recipient for Gmail compose action.",
                )
                gmail_url = _build_gmail_compose_url(
                    to_email=to_email,
                    subject="Due Diligence app link",
                    body=f"Please review the Due Diligence app:\n{app_url}",
                )
                _link_button("✉️ Open in Gmail", gmail_url)
            with st.expander("Open app inside this tab", expanded=False):
                if st.checkbox("Embed external DD app", key="dd_embed_external_app"):
                    components.iframe(app_url, height=900, scrolling=True)
        else:
            st.info(
                "External DD app URL is not configured yet. "
                "Set `DUE_DILIGENCE_APP_URL` (or `DD_APP_URL`) in secrets/.env."
            )
            st.markdown("**Run locally**")
            st.code(
                "cd DD\n"
                "python -m pip install -r requirements.txt\n"
                "python -m app.scripts.init_db\n"
                "streamlit run app/main.py",
                language="bash",
            )
            st.caption(
                "After deployment, set DUE_DILIGENCE_APP_URL so this tab can open/embed the live app."
            )
