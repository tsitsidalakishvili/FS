import streamlit as st
import streamlit.components.v1 as components

from crm.config import get_config


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

        st.markdown("### How and when blocks connect")
        st.dataframe(
            [
                {
                    "Trigger": "User opens Due Diligence tab",
                    "Connected blocks": "CRM Context -> Entity Resolution",
                    "Output": "Known person/company context loaded for checks",
                },
                {
                    "Trigger": "User clicks enrichment actions",
                    "Connected blocks": "Entity Resolution -> Enrichment -> Graph",
                    "Output": "External-source entities, relationships, and evidence",
                },
                {
                    "Trigger": "Weekly scheduler runs",
                    "Connected blocks": "Weekly Monitoring -> Graph",
                    "Output": "Fresh NewsArticle nodes + MENTIONED_IN links",
                },
                {
                    "Trigger": "Risk analysis requested",
                    "Connected blocks": "Graph -> Risk View",
                    "Output": "2-hop risk neighborhood and red-flag entities",
                },
                {
                    "Trigger": "Report generated",
                    "Connected blocks": "Graph -> Report -> CRM Actions",
                    "Output": "Evidence summary + follow-up/escalation tasks",
                },
            ],
            use_container_width=True,
        )

        st.markdown("### Phase 1 implementation status")
        st.success("Completed: Weekly monitoring now links entities to news with MENTIONED_IN.")
        st.success("Completed: Search now uses Neo4j fulltext indexes for Person/Company.")
        st.success("Completed: Entity and relationship writes now stamp source + ingestion timestamps.")

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
            st.markdown(f"[Open Due Diligence app in new tab]({app_url})")
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
