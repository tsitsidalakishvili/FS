import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse

from crm.analytics.people import load_supporter_summary
from crm.config import FEEDBACK_EMAIL_TO, get_config
from crm.data.competitors import (
    COMPETITOR_TYPES,
    delete_competitor,
    list_competitors,
    upsert_competitor,
)

OPENSANCTIONS_DATASET_OPTIONS = (
    "ge_declarations",
    "ge_ot_list",
    "ext_ge_company_registry",
    "wd_peps",
    "sanctions",
    "default",
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


def _build_dd_launch_url(
    app_url: str,
    *,
    subject_name: str,
    subject_type: str,
    start_mode: str,
    use_wikidata: bool,
    use_wikipedia: bool,
    use_opensanctions: bool,
    use_news: bool,
    use_gdelt: bool,
    opensanctions_dataset: str,
    autorun: bool = False,
    crm_subject_source: str = "",
    crm_subject_id: str = "",
) -> str:
    return _append_query_params(
        app_url,
        {
            "subject": subject_name,
            "subject_type": subject_type,
            "start_mode": start_mode.replace(" ", "_").lower(),
            "use_wikidata": "1" if use_wikidata else "0",
            "use_wikipedia": "1" if use_wikipedia else "0",
            "use_opensanctions": "1" if use_opensanctions else "0",
            "use_news": "1" if use_news else "0",
            "use_gdelt": "1" if use_gdelt else "0",
            "opensanctions_dataset": opensanctions_dataset,
            "autorun": "1" if autorun else "0",
            "crm_subject_source": crm_subject_source,
            "crm_subject_id": crm_subject_id,
        },
    )


def _selected_dd_sources(
    *,
    use_wikidata: bool,
    use_wikipedia: bool,
    use_opensanctions: bool,
    use_news: bool,
    use_gdelt: bool,
    opensanctions_dataset: str,
) -> list[str]:
    sources: list[str] = []
    if use_wikidata:
        sources.append("Wikidata")
    if use_wikipedia:
        sources.append("Wikipedia")
    if use_opensanctions:
        sources.append(f"OpenSanctions ({opensanctions_dataset})")
    if use_news:
        sources.append("NewsAPI")
    if use_gdelt:
        sources.append("GDELT")
    return sources


def _render_architecture_card(title: str, concept: str, outcome: str, tone: str = "default") -> None:
    palettes = {
        "default": {"bg": "#F8FAFF", "border": "#9FB8E8", "title": "#1E3A8A"},
        "entry": {"bg": "#FFF7ED", "border": "#FDBA74", "title": "#9A3412"},
        "monitor": {"bg": "#ECFDF3", "border": "#86EFAC", "title": "#166534"},
    }
    palette = palettes.get(tone, palettes["default"])
    st.markdown(
        f"""
        <div style="
            border: 1px solid {palette['border']};
            background: {palette['bg']};
            border-radius: 10px;
            padding: 8px 10px;
            margin: 0;
            min-height: 132px;
        ">
            <div style="font-size: 14px; font-weight: 700; color: {palette['title']}; margin-bottom: 4px;">
                {title}
            </div>
            <div style="font-size: 12px; margin-bottom: 3px;">
                <b>Concept:</b> {concept}
            </div>
            <div style="font-size: 12px;">
                <b>Outcome:</b> {outcome}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_due_diligence_how_it_works() -> None:
    st.markdown("### Workflow architecture")
    html = """
    <div style="width:100%; background:#ffffff; border:1px solid #E2E8F0; border-radius:12px; padding:8px;">
      <svg viewBox="0 0 1280 760" width="100%" height="740" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748B"></path>
          </marker>
          <filter id="shadow" x="-10%" y="-10%" width="130%" height="130%">
            <feDropShadow dx="0" dy="1" stdDeviation="1.2" flood-color="#CBD5E1" flood-opacity="0.9"/>
          </filter>
        </defs>

        <rect x="20" y="18" width="1240" height="724" rx="12" fill="#F8FAFC" stroke="#E2E8F0"/>

        <!-- Entry row -->
        <rect x="50" y="55" width="260" height="120" rx="10" fill="#EFF6FF" stroke="#93C5FD" filter="url(#shadow)"/>
        <text x="66" y="82" font-size="16" font-weight="700" fill="#1E3A8A">CRM Context</text>
        <text x="66" y="104" font-size="13" fill="#334155">Profile / Task / Event trigger</text>
        <text x="66" y="124" font-size="13" fill="#334155">Outcome: scoped investigation</text>

        <rect x="350" y="55" width="260" height="120" rx="10" fill="#FFF7ED" stroke="#FDBA74" filter="url(#shadow)"/>
        <text x="366" y="82" font-size="16" font-weight="700" fill="#9A3412">Competitor Lead</text>
        <text x="366" y="104" font-size="13" fill="#7C2D12">External person/company trigger</text>
        <text x="366" y="124" font-size="13" fill="#7C2D12">Outcome: direct intake subject</text>

        <rect x="680" y="55" width="280" height="120" rx="10" fill="#EEF2FF" stroke="#A5B4FC" filter="url(#shadow)"/>
        <text x="696" y="82" font-size="16" font-weight="700" fill="#312E81">1) Start Point</text>
        <text x="696" y="104" font-size="13" fill="#3730A3">Normalize entry path</text>
        <text x="696" y="124" font-size="13" fill="#3730A3">Outcome: one investigation context</text>

        <!-- Analysis row -->
        <rect x="50" y="245" width="280" height="130" rx="10" fill="#F8FAFF" stroke="#9FB8E8" filter="url(#shadow)"/>
        <text x="66" y="272" font-size="16" font-weight="700" fill="#1E3A8A">2) Entity Resolution</text>
        <text x="66" y="295" font-size="13" fill="#334155">Match / create canonical IDs</text>
        <text x="66" y="315" font-size="13" fill="#334155">Outcome: deduplicated subject</text>

        <rect x="360" y="245" width="280" height="130" rx="10" fill="#F8FAFF" stroke="#9FB8E8" filter="url(#shadow)"/>
        <text x="376" y="272" font-size="16" font-weight="700" fill="#1E3A8A">3) Enrichment</text>
        <text x="376" y="295" font-size="13" fill="#334155">Wikidata / OpenSanctions / News</text>
        <text x="376" y="315" font-size="13" fill="#334155">Outcome: source-linked facts</text>

        <rect x="670" y="245" width="280" height="130" rx="10" fill="#F8FAFF" stroke="#9FB8E8" filter="url(#shadow)"/>
        <text x="686" y="272" font-size="16" font-weight="700" fill="#1E3A8A">4) Neo4j Graph</text>
        <text x="686" y="295" font-size="13" fill="#334155">Nodes + relationships + provenance</text>
        <text x="686" y="315" font-size="13" fill="#334155">Outcome: queryable network state</text>

        <rect x="980" y="245" width="250" height="130" rx="10" fill="#F8FAFF" stroke="#9FB8E8" filter="url(#shadow)"/>
        <text x="996" y="272" font-size="16" font-weight="700" fill="#1E3A8A">5) Risk View</text>
        <text x="996" y="295" font-size="13" fill="#334155">2-hop exposure checks</text>
        <text x="996" y="315" font-size="13" fill="#334155">Outcome: prioritized risk signals</text>

        <!-- Decisions row -->
        <rect x="250" y="465" width="280" height="130" rx="10" fill="#F8FAFF" stroke="#9FB8E8" filter="url(#shadow)"/>
        <text x="266" y="492" font-size="16" font-weight="700" fill="#1E3A8A">6) Report</text>
        <text x="266" y="515" font-size="13" fill="#334155">Evidence-backed findings summary</text>
        <text x="266" y="535" font-size="13" fill="#334155">Outcome: decision-ready PDF</text>

        <rect x="560" y="465" width="280" height="130" rx="10" fill="#F8FAFF" stroke="#9FB8E8" filter="url(#shadow)"/>
        <text x="576" y="492" font-size="16" font-weight="700" fill="#1E3A8A">7) CRM Actions</text>
        <text x="576" y="515" font-size="13" fill="#334155">Follow-up / escalate / monitor</text>
        <text x="576" y="535" font-size="13" fill="#334155">Outcome: accountable next steps</text>

        <rect x="870" y="465" width="360" height="130" rx="10" fill="#ECFDF3" stroke="#86EFAC" filter="url(#shadow)"/>
        <text x="886" y="492" font-size="16" font-weight="700" fill="#166534">Weekly Monitoring</text>
        <text x="886" y="515" font-size="13" fill="#14532D">Refresh mentions and new media signals</text>
        <text x="886" y="535" font-size="13" fill="#14532D">Outcome: continuously updated risk posture</text>

        <!-- Connectors -->
        <path d="M 310 115 L 680 115" stroke="#64748B" stroke-width="2" fill="none" marker-end="url(#arrow)"/>
        <path d="M 610 115 L 680 115" stroke="#64748B" stroke-width="2" fill="none" marker-end="url(#arrow)"/>
        <path d="M 820 175 L 820 235 L 190 235 L 190 245" stroke="#64748B" stroke-width="2" fill="none" marker-end="url(#arrow)"/>
        <path d="M 330 310 L 360 310" stroke="#64748B" stroke-width="2" fill="none" marker-end="url(#arrow)"/>
        <path d="M 640 310 L 670 310" stroke="#64748B" stroke-width="2" fill="none" marker-end="url(#arrow)"/>
        <path d="M 950 310 L 980 310" stroke="#64748B" stroke-width="2" fill="none" marker-end="url(#arrow)"/>
        <path d="M 1105 375 L 1105 430 L 390 430 L 390 465" stroke="#64748B" stroke-width="2" fill="none" marker-end="url(#arrow)"/>
        <path d="M 530 530 L 560 530" stroke="#64748B" stroke-width="2" fill="none" marker-end="url(#arrow)"/>
        <path d="M 1050 465 L 1050 390 L 810 390 L 810 375" stroke="#16A34A" stroke-width="2.2" fill="none" marker-end="url(#arrow)"/>

        <!-- Labels -->
        <text x="700" y="33" font-size="14" fill="#475569" text-anchor="middle">ENTRY</text>
        <text x="640" y="223" font-size="14" fill="#475569" text-anchor="middle">ANALYSIS</text>
        <text x="640" y="443" font-size="14" fill="#475569" text-anchor="middle">DECISIONS & OPERATIONS</text>
      </svg>
    </div>
    """
    components.html(html, height=770, scrolling=False)


def _render_competitor_watchlist() -> tuple[str, str, str]:
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
        return "", "", ""

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
        return "", "", ""

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
        return name, competitor_type, competitor_id
    return "", "", ""


def render_due_diligence_page():
    st.subheader("Due Diligence")
    st.caption(
        "Select person/organization, check CRM + competitors, run analysis, then launch workflow."
    )
    app_url = (
        str(get_config("DUE_DILIGENCE_APP_URL") or "").strip()
        or str(get_config("DD_APP_URL") or "").strip()
    )
    st.session_state.setdefault("dd_cfg_opensanctions_dataset", "ge_declarations")
    st.session_state.setdefault("dd_launch_url_override", "")

    def _set_subject(
        name: str,
        subject_type: str,
        start_mode: str,
        *,
        crm_subject_source: str = "",
        crm_subject_id: str = "",
    ) -> None:
        st.session_state["dd_subject_name"] = str(name or "").strip()
        st.session_state["dd_subject_type"] = str(subject_type or "").strip()
        st.session_state["dd_start_mode"] = str(start_mode or "").strip()
        st.session_state["dd_subject_source"] = str(crm_subject_source or "").strip()
        st.session_state["dd_subject_source_id"] = str(crm_subject_id or "").strip()

    analysis_tab, configure_tab, watchlist_tab, launch_tab = st.tabs(
        ["Analysis", "Configure", "Watchlist", "Launch"]
    )

    with analysis_tab:
        st.markdown("#### Subject analysis")
        analysis_cols = st.columns([3, 1, 1])
        with analysis_cols[0]:
            default_subject = str(st.session_state.get("dd_subject_name") or "").strip()
            if "dd_analysis_subject_name" not in st.session_state and default_subject:
                st.session_state["dd_analysis_subject_name"] = default_subject
            subject_name = st.text_input(
                "Person / organization",
                key="dd_analysis_subject_name",
                placeholder="Enter full name or organization...",
            ).strip()
        with analysis_cols[1]:
            subject_type = st.selectbox(
                "Type",
                ["Person", "Organization"],
                key="dd_analysis_subject_type",
            )
        with analysis_cols[2]:
            st.write("")
            st.write("")
            if st.button("Set active subject", key="dd_set_subject_analysis", use_container_width=True):
                if subject_name:
                    _set_subject(subject_name, subject_type, "Analysis")
                    st.success(f"Active subject: {subject_name} ({subject_type})")
                else:
                    st.warning("Enter a subject name first.")

        if st.button("Run internal checks", key="dd_run_internal_checks"):
            st.session_state["dd_run_internal_checks"] = True

        run_checks = bool(st.session_state.get("dd_run_internal_checks", False))
        if run_checks and subject_name:
            query = subject_name.lower()
            crm_df = load_supporter_summary()
            if crm_df.empty:
                crm_matches = crm_df
            else:
                name_series = (
                    crm_df["fullName"].astype(str).str.lower()
                    if "fullName" in crm_df.columns
                    else crm_df.index.to_series().map(lambda _: "")
                )
                email_series = (
                    crm_df["email"].astype(str).str.lower()
                    if "email" in crm_df.columns
                    else crm_df.index.to_series().map(lambda _: "")
                )
                searchable = name_series + " " + email_series
                crm_matches = crm_df[searchable.str.contains(query, na=False)]

            comp_df = list_competitors()
            if comp_df.empty:
                comp_matches = comp_df
            else:
                comp_searchable = (
                    comp_df["name"].astype(str).str.lower()
                    if "name" in comp_df.columns
                    else comp_df.index.to_series().map(lambda _: "")
                )
                comp_matches = comp_df[comp_searchable.str.contains(query, na=False)]

            metric_cols = st.columns(3)
            metric_cols[0].metric("CRM matches", len(crm_matches))
            metric_cols[1].metric("Competitor matches", len(comp_matches))
            metric_cols[2].metric(
                "Subject status",
                "Known"
                if (len(crm_matches) + len(comp_matches)) > 0
                else "New",
            )

            crm_match_cols = [c for c in ["fullName", "email", "group"] if c in crm_matches.columns]
            comp_match_cols = [c for c in ["name", "competitorType", "notes"] if c in comp_matches.columns]

            st.markdown("##### CRM check results")
            if crm_matches.empty:
                st.caption("No CRM records matched this subject.")
            elif crm_match_cols:
                st.dataframe(crm_matches[crm_match_cols], use_container_width=True, height=180)

            st.markdown("##### Competitor check results")
            if comp_matches.empty:
                st.caption("No competitor records matched this subject.")
            elif comp_match_cols:
                st.dataframe(comp_matches[comp_match_cols], use_container_width=True, height=180)

        st.markdown("---")
        st.markdown("##### External analysis sources")
        src_cols = st.columns(5)
        with src_cols[0]:
            st.checkbox("Wikidata", key="dd_cfg_use_wikidata", value=True)
        with src_cols[1]:
            st.checkbox("Wikipedia", key="dd_cfg_use_wikipedia", value=True)
        with src_cols[2]:
            st.checkbox("OpenSanctions", key="dd_cfg_use_opensanctions", value=True)
        with src_cols[3]:
            st.checkbox("NewsAPI", key="dd_cfg_use_news", value=True)
        with src_cols[4]:
            st.checkbox("GDELT", key="dd_cfg_use_gdelt", value=True)
        dataset_options = list(OPENSANCTIONS_DATASET_OPTIONS) + ["custom"]
        current_dataset = str(st.session_state.get("dd_cfg_opensanctions_dataset") or "").strip()
        current_dataset = current_dataset or "ge_declarations"
        default_dataset = current_dataset if current_dataset in OPENSANCTIONS_DATASET_OPTIONS else "custom"
        selected_dataset = st.selectbox(
            "OpenSanctions dataset",
            options=dataset_options,
            index=dataset_options.index(default_dataset),
            key="dd_cfg_opensanctions_dataset_choice",
            help="Georgia declarations are the default for public official due diligence.",
        )
        if selected_dataset == "custom":
            custom_dataset = st.text_input(
                "Custom OpenSanctions dataset",
                value=current_dataset if current_dataset not in OPENSANCTIONS_DATASET_OPTIONS else "",
                key="dd_cfg_opensanctions_dataset_custom",
                help="Examples: ge_declarations, ge_ot_list, ext_ge_company_registry, wd_peps",
            ).strip()
            st.session_state["dd_cfg_opensanctions_dataset"] = custom_dataset or "ge_declarations"
        else:
            st.session_state["dd_cfg_opensanctions_dataset"] = selected_dataset
        if st.button("Run analysis", key="dd_run_external_analysis"):
            if not subject_name:
                st.warning("Set a subject first.")
            else:
                current_subject_name = str(st.session_state.get("dd_subject_name") or "").strip()
                current_subject_type = str(st.session_state.get("dd_subject_type") or "").strip()
                crm_subject_source = ""
                crm_subject_id = ""
                if current_subject_name == subject_name and current_subject_type == subject_type:
                    crm_subject_source = str(
                        st.session_state.get("dd_subject_source") or ""
                    ).strip()
                    crm_subject_id = str(
                        st.session_state.get("dd_subject_source_id") or ""
                    ).strip()
                _set_subject(
                    subject_name,
                    subject_type,
                    "Analysis",
                    crm_subject_source=crm_subject_source,
                    crm_subject_id=crm_subject_id,
                )
                enabled = []
                if st.session_state.get("dd_cfg_use_wikidata"):
                    enabled.append("Wikidata")
                if st.session_state.get("dd_cfg_use_wikipedia"):
                    enabled.append("Wikipedia")
                if st.session_state.get("dd_cfg_use_opensanctions"):
                    enabled.append(
                        f"OpenSanctions ({st.session_state.get('dd_cfg_opensanctions_dataset')})"
                    )
                if st.session_state.get("dd_cfg_use_news"):
                    enabled.append("NewsAPI")
                if st.session_state.get("dd_cfg_use_gdelt"):
                    enabled.append("GDELT")
                autorun_launch_url = _build_dd_launch_url(
                    app_url,
                    subject_name=subject_name,
                    subject_type=subject_type,
                    start_mode="Analysis",
                    use_wikidata=bool(st.session_state.get("dd_cfg_use_wikidata")),
                    use_wikipedia=bool(st.session_state.get("dd_cfg_use_wikipedia")),
                    use_opensanctions=bool(st.session_state.get("dd_cfg_use_opensanctions")),
                    use_news=bool(st.session_state.get("dd_cfg_use_news")),
                    use_gdelt=bool(st.session_state.get("dd_cfg_use_gdelt")),
                    opensanctions_dataset=str(
                        st.session_state.get("dd_cfg_opensanctions_dataset") or "ge_declarations"
                    ),
                    autorun=True,
                    crm_subject_source=crm_subject_source,
                    crm_subject_id=crm_subject_id,
                )
                if app_url:
                    st.success(
                        f"Due Diligence launch is ready for {subject_name} ({subject_type}) using: "
                        f"{', '.join(enabled) if enabled else 'no sources selected'}."
                    )
                    st.caption(
                        "The DD app shows a live progress bar while each selected source is running."
                    )
                    _link_button("🚀 Open DD app and run selected sources", autorun_launch_url)
                else:
                    st.info(
                        "External DD app URL is not configured yet. Use the Launch tab for the local run instructions."
                    )

    with configure_tab:
        st.markdown("#### Configure")
        cfg_data_tab, cfg_sources_tab = st.tabs(["CRM & Competitors", "Public sources"])
        with cfg_data_tab:
            summary_df = load_supporter_summary()
            total_people = len(summary_df)
            if not summary_df.empty and "group" in summary_df.columns:
                total_supporters = int((summary_df["group"] == "Supporter").sum())
                total_members = int((summary_df["group"] == "Member").sum())
            else:
                total_supporters = 0
                total_members = 0
            mcols = st.columns(3)
            mcols[0].metric("CRM people", total_people)
            mcols[1].metric("Supporters", total_supporters)
            mcols[2].metric("Members", total_members)
            st.markdown("##### Competitor records")
            selected_name, selected_type, selected_competitor_id = _render_competitor_watchlist()
            if selected_name and selected_type:
                if st.button("Set selected as active subject", key="dd_cfg_use_selected_subject"):
                    _set_subject(
                        selected_name,
                        selected_type,
                        "Configure",
                        crm_subject_source="competitor",
                        crm_subject_id=selected_competitor_id,
                    )
                    st.success(f"Active subject set: {selected_name} ({selected_type})")
                    st.rerun()

        with cfg_sources_tab:
            st.caption("Control which external sources are used during analysis.")
            st.checkbox("Enable Wikidata", key="dd_cfg_use_wikidata")
            st.checkbox("Enable Wikipedia", key="dd_cfg_use_wikipedia")
            st.checkbox("Enable OpenSanctions", key="dd_cfg_use_opensanctions")
            st.checkbox("Enable NewsAPI", key="dd_cfg_use_news")
            st.checkbox("Enable GDELT", key="dd_cfg_use_gdelt")
            st.text_input(
                "Selected OpenSanctions dataset",
                key="dd_cfg_opensanctions_dataset",
                help="Default launch dataset for the DD app.",
            )
            st.markdown("##### Source connection status")
            open_key = str(get_config("OPENSANCTIONS_API_KEY") or "").strip()
            news_key = str(get_config("NEWS_API_KEY") or "").strip()
            st.write(f"- OpenSanctions API key: {'Configured' if open_key else 'Not configured'}")
            st.write(f"- News API key: {'Configured' if news_key else 'Not configured'}")
            st.write("- Wikipedia: Public source (no key required)")
            st.write("- GDELT: Public source (no key required)")
            st.caption(
                "API keys and base URLs are managed in .env / Streamlit secrets."
            )

    with watchlist_tab:
        st.markdown("#### Watchlist")
        st.caption("Save competitors and optionally use one as your intake subject.")
        selected_name, selected_type, selected_competitor_id = _render_competitor_watchlist()
        if selected_name and selected_type:
            st.success(f"Selected watchlist item: {selected_name} ({selected_type})")
            if st.button("Use selected as intake subject", key="dd_use_watchlist_subject"):
                _set_subject(
                    selected_name,
                    selected_type,
                    "Watchlist",
                    crm_subject_source="competitor",
                    crm_subject_id=selected_competitor_id,
                )
                st.success("Watchlist subject set for intake.")
                st.rerun()

    with launch_tab:
        st.markdown("#### Launch")
        subject_name = str(st.session_state.get("dd_subject_name") or "").strip()
        subject_type = str(st.session_state.get("dd_subject_type") or "").strip()
        start_mode = str(st.session_state.get("dd_start_mode") or "Analysis")
        crm_subject_source = str(st.session_state.get("dd_subject_source") or "").strip()
        crm_subject_id = str(st.session_state.get("dd_subject_source_id") or "").strip()
        if subject_name:
            st.success(f"Launch subject: {subject_name} ({subject_type})")
        else:
            st.warning("No subject selected yet. Set one in Analysis or Watchlist.")

        use_wikidata = bool(st.session_state.get("dd_cfg_use_wikidata", True))
        use_wikipedia = bool(st.session_state.get("dd_cfg_use_wikipedia", True))
        use_opensanctions = bool(st.session_state.get("dd_cfg_use_opensanctions", True))
        use_news = bool(st.session_state.get("dd_cfg_use_news", True))
        use_gdelt = bool(st.session_state.get("dd_cfg_use_gdelt", True))
        opensanctions_dataset = str(
            st.session_state.get("dd_cfg_opensanctions_dataset") or "ge_declarations"
        ).strip() or "ge_declarations"
        selected_sources = _selected_dd_sources(
            use_wikidata=use_wikidata,
            use_wikipedia=use_wikipedia,
            use_opensanctions=use_opensanctions,
            use_news=use_news,
            use_gdelt=use_gdelt,
            opensanctions_dataset=opensanctions_dataset,
        )
        launch_payload = {
            "subject": subject_name,
            "subject_type": subject_type,
            "start_mode": start_mode.replace(" ", "_").lower(),
            "use_wikidata": "1" if use_wikidata else "0",
            "use_wikipedia": "1" if use_wikipedia else "0",
            "use_opensanctions": "1" if use_opensanctions else "0",
            "use_news": "1" if use_news else "0",
            "use_gdelt": "1" if use_gdelt else "0",
            "opensanctions_dataset": opensanctions_dataset,
            "crm_subject_source": crm_subject_source,
            "crm_subject_id": crm_subject_id,
        }
        summary_cols = st.columns(4)
        summary_cols[0].metric("Sources selected", len(selected_sources))
        summary_cols[1].metric("Start mode", start_mode)
        summary_cols[2].metric(
            "Intake source",
            crm_subject_source.replace("_", " ").title() if crm_subject_source else "Manual",
        )
        summary_cols[3].metric(
            "OpenSanctions dataset",
            opensanctions_dataset,
        )
        if selected_sources:
            st.caption("Selected sources: " + ", ".join(selected_sources))
        else:
            st.caption("No external sources are selected for launch.")

        st.markdown("##### App endpoint")
        if app_url:
            st.success("External Due Diligence app URL is configured.")
        else:
            st.info(
                "No permanent DD app URL is configured yet. "
                "You can still paste a temporary/local DD app URL below."
            )
        st.text_input(
            "Configured DD app URL",
            value=app_url,
            key="dd_app_url_preview",
            disabled=True,
        )
        override_help = (
            "Optional one-off DD URL for local testing or a temporary deployment. "
            "Example: http://localhost:8502"
        )
        override_url = st.text_input(
            "Temporary DD app URL override",
            key="dd_launch_url_override",
            placeholder="http://localhost:8502",
            help=override_help,
        ).strip()
        effective_app_url = override_url or app_url
        if override_url:
            st.caption("Launch tab is using the temporary override URL above.")

        app_launch_url = _build_dd_launch_url(
            effective_app_url,
            subject_name=subject_name,
            subject_type=subject_type,
            start_mode=start_mode,
            use_wikidata=use_wikidata,
            use_wikipedia=use_wikipedia,
            use_opensanctions=use_opensanctions,
            use_news=use_news,
            use_gdelt=use_gdelt,
            opensanctions_dataset=opensanctions_dataset,
            crm_subject_source=crm_subject_source,
            crm_subject_id=crm_subject_id,
        )
        autorun_launch_url = _build_dd_launch_url(
            effective_app_url,
            subject_name=subject_name,
            subject_type=subject_type,
            start_mode=start_mode,
            use_wikidata=use_wikidata,
            use_wikipedia=use_wikipedia,
            use_opensanctions=use_opensanctions,
            use_news=use_news,
            use_gdelt=use_gdelt,
            opensanctions_dataset=opensanctions_dataset,
            autorun=True,
            crm_subject_source=crm_subject_source,
            crm_subject_id=crm_subject_id,
        )

        st.markdown("##### Launch URLs")
        st.text_input(
            "Open DD app URL",
            value=app_launch_url or "",
            key="dd_launch_url_preview",
        )
        st.text_input(
            "Open and run sources URL",
            value=autorun_launch_url or "",
            key="dd_autorun_url_preview",
        )
        with st.expander("Launch payload / query contract", expanded=False):
            st.json(launch_payload)

        if effective_app_url:
            action_cols = st.columns(4)
            with action_cols[0]:
                _link_button("🚀 Open DD app", app_launch_url or effective_app_url)
            with action_cols[1]:
                _link_button("▶️ Open and run sources", autorun_launch_url or effective_app_url)
            with action_cols[2]:
                if st.button("🖼️ Toggle embed", key="dd_embed_toggle", use_container_width=True):
                    st.session_state["dd_embed_external_app"] = not bool(
                        st.session_state.get("dd_embed_external_app")
                    )
            with action_cols[3]:
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
                        f"Wikidata: {'on' if use_wikidata else 'off'}\n"
                        f"Wikipedia: {'on' if use_wikipedia else 'off'}\n"
                        f"OpenSanctions: {'on' if use_opensanctions else 'off'}\n"
                        f"OpenSanctions dataset: {opensanctions_dataset}\n"
                        f"NewsAPI: {'on' if use_news else 'off'}\n"
                        f"GDELT: {'on' if use_gdelt else 'off'}\n\n"
                        f"Due Diligence app:\n"
                        f"{autorun_launch_url or app_launch_url or effective_app_url}"
                    ),
                )
                _link_button("✉️ Open in Gmail", gmail_url)
            with st.expander("Open app inside this tab", expanded=False):
                if st.checkbox("Embed external DD app", key="dd_embed_external_app"):
                    components.iframe(
                        app_launch_url or effective_app_url, height=900, scrolling=True
                    )
        else:
            st.markdown("##### Run locally")
            st.code(
                "PORT=8502\n"
                "cd DD\n"
                "python -m pip install -r requirements.txt\n"
                "python -m app.scripts.init_db\n"
                "streamlit run app/main.py --server.port $PORT",
                language="bash",
            )
            st.caption(
                "After the DD app is running, paste its URL above as a temporary override "
                "or set DUE_DILIGENCE_APP_URL / DD_APP_URL in .env or Streamlit secrets."
            )
            local_example_url = _build_dd_launch_url(
                "http://localhost:8502",
                subject_name=subject_name,
                subject_type=subject_type,
                start_mode=start_mode,
                use_wikidata=use_wikidata,
                use_wikipedia=use_wikipedia,
                use_opensanctions=use_opensanctions,
                use_news=use_news,
                use_gdelt=use_gdelt,
                opensanctions_dataset=opensanctions_dataset,
                autorun=True,
                crm_subject_source=crm_subject_source,
                crm_subject_id=crm_subject_id,
            )
            st.text_input(
                "Example local autorun URL",
                value=local_example_url,
                key="dd_local_example_url_preview",
            )
