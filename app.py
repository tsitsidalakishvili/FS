from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import streamlit as st

import crm.db.neo4j as neo4j_db
from crm.analytics.people import clear_people_caches
from crm.clients.deliberation import delib_api_get
from crm.config import (
    NEO4J_SANDBOX_DATABASE,
    NEO4J_SANDBOX_PASSWORD,
    NEO4J_SANDBOX_URI,
    NEO4J_SANDBOX_USER,
    PUBLIC_ONLY,
    SUPPORTER_ACCESS_CODE,
)
from crm.db.neo4j import init_driver
from crm.services.feedback import render_feedback_widget
from crm.data.events import list_events
from crm.data.people import get_distinct_values, load_person_profile, search_people
from crm.data.segments import list_segments, load_segment_filter, run_segment
from crm.data.tasks import list_tasks
from crm.ui.components.questionnaire import render_survey_page
from crm.ui.pages.admin import render_admin_page
from crm.ui.pages.dashboard import render_dashboard_page
from crm.ui.pages.data import render_data_page
from crm.ui.pages.deliberation import render_deliberation as render_deliberation_page
from crm.ui.pages.events import render_events_page
from crm.ui.pages.map import render_map_page
from crm.ui.pages.outreach import render_outreach_page
from crm.ui.pages.profiles import render_profiles_tab as render_profiles_tab_page
from crm.ui.pages.segments import render_segments_tab as render_segments_tab_page
from crm.ui.pages.tasks import render_tasks_tab as render_tasks_tab_page
from crm.ui.pages.volunteers import render_volunteers_page


st.set_page_config(page_title="Freedom Square CRM", layout="wide")

st.markdown(
    """
<style>
[data-testid="stTooltipIcon"] {
  opacity: 1 !important;
  color: #6b7280 !important;
}
[data-testid="stTooltipIcon"] svg {
  width: 18px !important;
  height: 18px !important;
}
</style>
""",
    unsafe_allow_html=True,
)


@dataclass(frozen=True)
class AppPage:
    label: str
    render: Callable[[], None]


def _get_query_param(name: str) -> Optional[str]:
    try:
        value = st.query_params.get(name)
    except Exception:
        params = st.experimental_get_query_params()
        value = params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _set_query_param(name: str, value: str) -> None:
    try:
        st.query_params[name] = value
    except Exception:
        st.experimental_set_query_params(**{name: value})


def _handle_questionnaire_routes() -> None:
    questionnaire_kind = _get_query_param("questionnaire")
    if questionnaire_kind:
        kind = str(questionnaire_kind).strip().lower()
        if kind in {"deliberation", "deliberation_admin"}:
            convo_id = _get_query_param("conversation_id") or _get_query_param("conversation")
            if convo_id:
                conversations = delib_api_get("/conversations", show_error=False) or []
                convo_topic = None
                for convo in conversations:
                    if str(convo.get("id")) == str(convo_id):
                        convo_topic = convo.get("topic")
                        break
                if convo_topic:
                    st.session_state["delib_conversation_id"] = convo_id
                    st.session_state["delib_conversation_select"] = convo_topic
            render_deliberation_page(public_only=(kind == "deliberation"))
            st.stop()
        st.error("Unknown questionnaire type.")
        st.stop()

    survey_id = _get_query_param("survey")
    if survey_id:
        render_survey_page(str(survey_id).strip())
        st.stop()


def _render_people_workspace() -> None:
    st.subheader("People")
    st.caption("Profiles and follow-ups in one place.")
    profiles_tab, tasks_tab = st.tabs(["Profiles", "Tasks / Follow-ups"])
    with profiles_tab:
        render_profiles_tab_page()
    with tasks_tab:
        render_tasks_tab_page()


def _crm_pages() -> List[AppPage]:
    return [
        AppPage("Dashboard", render_dashboard_page),
        AppPage("People", _render_people_workspace),
        AppPage("Segments", render_segments_tab_page),
        AppPage("Outreach", render_outreach_page),
        AppPage("Events", render_events_page),
        AppPage("Volunteers", render_volunteers_page),
        AppPage("Map", render_map_page),
        AppPage("Data", render_data_page),
        AppPage("Admin", render_admin_page),
        AppPage("Deliberation", lambda: render_deliberation_page(public_only=False)),
    ]


def _render_sidebar_data_controls() -> None:
    st.sidebar.markdown("### Data freshness")
    if st.sidebar.button(
        "Refresh cached data",
        key="refresh_cached_data",
        help="Clear lightweight app caches and fetch fresh data on next render.",
    ):
        clear_people_caches()
        list_tasks.clear()
        list_segments.clear()
        load_segment_filter.clear()
        run_segment.clear()
        list_events.clear()
        search_people.clear()
        load_person_profile.clear()
        get_distinct_values.clear()
        st.sidebar.success("Cache cleared.")


def _render_public_mode() -> None:
    st.info("Public view: deliberation participation only.")
    render_feedback_widget("Deliberation (Public)")
    render_deliberation_page(public_only=True)


def _ensure_db_connection() -> bool:
    st.sidebar.markdown("### Database")
    db_choice = st.sidebar.radio(
        "Connection",
        ["Local (Desktop)", "Sandbox (Web)"],
        index=0,
        key="db_connection_choice",
        help="Switch between your local Neo4j Desktop DB and Neo4j Sandbox.",
    )

    if db_choice == "Sandbox (Web)":
        if not NEO4J_SANDBOX_URI or not NEO4J_SANDBOX_PASSWORD:
            st.sidebar.warning(
                "Sandbox credentials missing. Set NEO4J_SANDBOX_URI and NEO4J_SANDBOX_PASSWORD."
            )
            return False
        return init_driver(
            uri=NEO4J_SANDBOX_URI,
            user=NEO4J_SANDBOX_USER,
            password=NEO4J_SANDBOX_PASSWORD,
            database=NEO4J_SANDBOX_DATABASE,
        )

    return init_driver()


def _main() -> None:
    _handle_questionnaire_routes()

    st.title("Freedom Square CRM")

    supporter_mode = not PUBLIC_ONLY
    if SUPPORTER_ACCESS_CODE:
        st.sidebar.markdown("### Access")
        entered_code = st.sidebar.text_input(
            "Supporter access code",
            type="password",
            help="If set in .env, this code gates access to CRM pages.",
        )
        supporter_mode = entered_code == SUPPORTER_ACCESS_CODE

    if not supporter_mode:
        _render_public_mode()
        return

    db_ok = _ensure_db_connection()
    has_db = db_ok and neo4j_db.driver is not None

    pages = _crm_pages() if has_db else [AppPage("Deliberation", lambda: render_deliberation_page(public_only=False))]
    page_by_label: Dict[str, AppPage] = {page.label: page for page in pages}
    labels = [page.label for page in pages]

    requested_page = (_get_query_param("page") or "").strip()
    nav_default = requested_page if requested_page in page_by_label else labels[0]
    if st.session_state.get("main_nav") not in labels:
        st.session_state["main_nav"] = nav_default

    nav_choice = st.sidebar.radio(
        "Navigate",
        labels,
        index=labels.index(nav_default),
        key="main_nav",
    )
    _set_query_param("page", nav_choice)

    _render_sidebar_data_controls()
    render_feedback_widget(nav_choice)

    if not has_db:
        st.warning("CRM database is unavailable. Deliberation remains available.")

    page_by_label[nav_choice].render()


if __name__ == "__main__":
    _main()
