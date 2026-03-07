import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse

from crm.config import FEEDBACK_EMAIL_TO, get_config
from crm.data.competitors import (
    COMPETITOR_TYPES,
    delete_competitor,
    list_competitors,
    upsert_competitor,
)


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


def _append_query_params(url: str, params: dict[str, str]) -> str:
    clean_url = str(url or "").strip()
    if not clean_url:
        return ""
    parsed = urlparse(clean_url)
    merged = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in params.items():
        text = str(value or "").strip()
        if text:
            merged[key] = text
    new_query = urlencode(merged, quote_via=quote_plus)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )


def _render_competitor_watchlist() -> tuple[str, str]:
    st.markdown("#### Competitor watchlist")
    with st.form("dd_competitor_form", clear_on_submit=True):
        form_cols = st.columns([2, 1])
        with form_cols[0]:
            comp_name = st.text_input("Competitor name")
        with form_cols[1]:
            comp_type = st.selectbox("Type", list(COMPETITOR_TYPES), index=0)
        comp_notes = st.text_area("Notes (optional)", height=80)
        save_clicked = st.form_submit_button("Save competitor")
    if save_clicked:
        if not str(comp_name or "").strip():
            st.warning("Competitor name is required.")
        elif upsert_competitor(comp_name, comp_type, comp_notes):
            st.success("Competitor saved.")
            st.rerun()
        else:
            st.error("Could not save competitor.")

    competitors_df = list_competitors()
    if competitors_df.empty:
        st.caption("No competitors saved yet.")
        return "", ""

    st.dataframe(competitors_df, use_container_width=True, height=220)
    options = {}
    for row in competitors_df.itertuples(index=False):
        competitor_id = str(getattr(row, "competitorId", "") or "").strip()
        name = str(getattr(row, "name", "") or "").strip()
        competitor_type = str(getattr(row, "competitorType", "") or "").strip()
        if not competitor_id or not name:
            continue
        label = f"{name} ({competitor_type})"
        if label in options:
            label = f"{label} [{competitor_id[:8]}]"
        options[label] = (name, competitor_type, competitor_id)

    if not options:
        return "", ""

    selected_label = st.selectbox(
        "Select competitor",
        options=[""] + list(options.keys()),
        key="dd_competitor_select",
    )
    selected = options.get(selected_label)
    if selected:
        name, competitor_type, competitor_id = selected
        delete_cols = st.columns([2, 1])
        with delete_cols[1]:
            if st.button("Delete selected", key="dd_delete_competitor"):
                if delete_competitor(competitor_id):
                    st.success("Competitor deleted.")
                    st.rerun()
                else:
                    st.error("Could not delete competitor.")
        return name, competitor_type
    return "", ""


def render_due_diligence_page():
    st.subheader("Due Diligence")
    how_it_works_tab, actual_app_tab = st.tabs(["How it works", "Actual app"])

    with how_it_works_tab:
        st.markdown("### Workflow architecture")
        dot = """
        digraph DDWorkflow {
          rankdir=TB;
          splines=ortho;
          graph [bgcolor="white", pad="0.25", nodesep="0.35", ranksep="0.45"];
          node [
            shape=box,
            style="rounded,filled",
            fillcolor="#F4F8FB",
            color="#2E5B7A",
            fontname="Helvetica",
            fontsize=23,
            penwidth=1.8,
            margin="0.12,0.10"
          ];
          edge [
            color="#4A6A85",
            fontname="Helvetica",
            fontsize=15,
            penwidth=1.6
          ];

          CRMContext [label="CRM Context\\nProfile / Task / Event\\nConcept: business reason for investigation\\nOutcome: investigation scope", margin="0.13,0.12"];
          CompetitorLead [label="Competitor Lead\\nPerson / Company\\nConcept: external trigger outside CRM record\\nOutcome: direct intake subject", fillcolor="#FFF5EB", color="#B96A1D", margin="0.13,0.12"];
          StartPoint [label="1) Start Point\\nChoose source and subject\\nConcept: normalize entry path\\nOutcome: one intake decision", shape=diamond, fillcolor="#EEF4FF", margin="0.13,0.12"];
          EntityResolution [label="2) Entity Resolution\\nMatch / create canonical ID\\nConcept: single source of truth\\nOutcome: deduplicated entity", margin="0.13,0.12"];
          Enrichment [label="3) Enrichment\\nWikidata / OpenSanctions / News\\nConcept: expand evidence graph\\nOutcome: new facts + linked sources", margin="0.13,0.12"];
          GraphStore [label="4) Neo4j Graph\\nStore nodes and relationships\\nConcept: provenance-first intelligence\\nOutcome: queryable network state", margin="0.13,0.12"];
          RiskView [label="5) Risk View\\n2-hop exposure checks\\nConcept: evaluate direct + indirect risk\\nOutcome: prioritized risk signals", margin="0.13,0.12"];
          Report [label="6) Report\\nEvidence-backed decision brief\\nConcept: explainable recommendations\\nOutcome: shareable PDF summary", margin="0.13,0.12"];
          ActionBacklog [label="7) CRM Actions\\nFollow-up / Escalate / Monitor\\nConcept: convert insight to operations\\nOutcome: accountable next steps", margin="0.13,0.12"];
          WeeklyMonitor [label="Weekly Monitoring\\nRefresh media and mentions\\nConcept: continuous risk detection\\nOutcome: updated risk posture", fillcolor="#EEF7EE", color="#2C7A4B", margin="0.13,0.12"];

          CRMContext -> StartPoint [label="from CRM"];
          CompetitorLead -> StartPoint [label="direct intake"];
          StartPoint -> EntityResolution [label="subject selected"];
          EntityResolution -> Enrichment [label="run checks"];
          EntityResolution -> GraphStore [label="entity exists"];
          Enrichment -> GraphStore [label="new entities + links"];
          GraphStore -> RiskView [label="query"];
          RiskView -> Report [label="export"];
          Report -> ActionBacklog [label="next steps"];
          WeeklyMonitor -> GraphStore [label="scheduled update"];
        }
        """
        try:
            st.graphviz_chart(dot, use_container_width=True)
        except Exception:
            st.code(dot, language="dot")

    with actual_app_tab:
        st.markdown("### Actual app")
        st.write(
            "Use this tab to access the working Due Diligence app and run live checks. "
            "Case workflow (Phase 2) will build on top of this foundation."
        )
        st.markdown("#### Investigation start point")
        start_mode = st.radio(
            "Start from",
            ["CRM context", "Competitor person", "Competitor company", "Competitor watchlist"],
            horizontal=True,
            key="dd_start_mode",
        )
        subject_name = ""
        subject_type = ""
        if start_mode == "CRM context":
            subject_name = st.text_input(
                "CRM subject (person/company)",
                key="dd_start_crm_subject",
                help="Use this when the investigation starts from CRM context.",
            ).strip()
            subject_type = st.selectbox(
                "CRM subject type",
                ["Person", "Company"],
                key="dd_start_crm_subject_type",
            )
        elif start_mode == "Competitor person":
            subject_name = st.text_input(
                "Competitor person name",
                key="dd_start_competitor_person",
                help="Investigate a competitor individual directly without opening a CRM profile first.",
            ).strip()
            subject_type = "Person"
        elif start_mode == "Competitor company":
            subject_name = st.text_input(
                "Competitor company name",
                key="dd_start_competitor_company",
                help="Investigate a competitor organization directly.",
            ).strip()
            subject_type = "Company"
        else:
            with st.expander("Manage competitor watchlist", expanded=True):
                selected_name, selected_type = _render_competitor_watchlist()
            subject_name = selected_name
            subject_type = selected_type

        if subject_name:
            st.success(f"Current DD subject: {subject_name} ({subject_type})")
        else:
            st.caption("Select or enter a subject to prefill DD app launch and Gmail share.")

        app_url = (
            str(get_config("DUE_DILIGENCE_APP_URL") or "").strip()
            or str(get_config("DD_APP_URL") or "").strip()
        )
        if app_url:
            st.success("External Due Diligence app is configured.")
            st.text_input("Configured app URL", value=app_url, key="dd_app_url_preview")
            app_launch_url = _append_query_params(
                app_url,
                {
                    "subject": subject_name,
                    "subject_type": subject_type,
                    "start_mode": start_mode.replace(" ", "_").lower(),
                },
            )
            action_cols = st.columns(3)
            with action_cols[0]:
                _link_button("🚀 Open DD app", app_launch_url or app_url)
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
                    subject="Due Diligence subject review",
                    body=(
                        f"Start mode: {start_mode}\n"
                        f"Subject: {subject_name or 'not set'}\n"
                        f"Subject type: {subject_type or 'not set'}\n\n"
                        f"Due Diligence app:\n{app_launch_url or app_url}"
                    ),
                )
                _link_button("✉️ Open in Gmail", gmail_url)
            with st.expander("Open app inside this tab", expanded=False):
                if st.checkbox("Embed external DD app", key="dd_embed_external_app"):
                    components.iframe(app_launch_url or app_url, height=900, scrolling=True)
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
