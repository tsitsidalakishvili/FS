from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st
from neo4j.exceptions import ServiceUnavailable
from requests.exceptions import HTTPError

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import get_settings
from app.graph.neo4j import Neo4jClient, Neo4jConfig
from app.graph.queries import get_entity, get_neighbors, get_risky_neighbors, search_entities
from app.graph.schema import initialize_schema
from app.graph.seed import seed_demo_graph, seed_sample_data
from app.graph.visualize import build_graph_html
from app.ingestion.ingest import apply_batch
from app.ingestion.models import Entity, IngestionBatch, Relationship
from app.ingestion.gdelt import fetch_gdelt_articles
from app.ingestion.news import fetch_news_articles
from app.ingestion.opensanctions import (
    fetch_opensanctions_match,
    get_georgia_dataset_profiles,
    fetch_opensanctions_search,
)
from app.ingestion.wikipedia import fetch_wikipedia_profile
from app.ingestion.wikidata import fetch_wikidata
from app.monitoring.weekly import run_weekly_monitoring
from app.reporting.dossier import build_dossier_snapshot, dossier_markdown
from app.reporting.pdf import generate_pdf_report


settings = get_settings()

st.set_page_config(page_title="Graph Due Diligence", layout="wide")


@st.cache_resource
def get_client() -> Neo4jClient:
    uri = st.session_state.get("neo4j_uri", settings.neo4j_uri)
    user = st.session_state.get("neo4j_user", settings.neo4j_user)
    password = st.session_state.get("neo4j_password", settings.neo4j_password)
    database = st.session_state.get("neo4j_database", settings.neo4j_database)
    return Neo4jClient(
        Neo4jConfig(
            uri=uri,
            user=user,
            password=password,
            database=database,
        )
    )


@st.cache_data(ttl=600, show_spinner=False)
def load_georgia_profiles(api_key: str | None) -> list[dict[str, object]]:
    if not api_key:
        return []
    return get_georgia_dataset_profiles(api_key)


client = get_client()

st.title("Graph-Centric Due Diligence Platform")
st.caption("Relationship-first intelligence with local Neo4j storage.")


def safe_neo4j_call(action: str, func, default=None, *args, **kwargs):
    try:
        return True, func(*args, **kwargs)
    except ServiceUnavailable:
        st.error("Neo4j connection error. Check URI, credentials, and network.")
        return False, default
    except Exception as exc:
        st.error(f"{action} failed: {exc}")
        return False, default


def _get_query_param(name: str) -> str | None:
    value = None
    try:
        value = st.query_params.get(name)
    except Exception:
        value = None
    if isinstance(value, list):
        return value[0] if value else None
    if value not in (None, ""):
        return str(value)
    try:
        params = st.experimental_get_query_params()
        fallback = params.get(name)
        if isinstance(fallback, list):
            return fallback[0] if fallback else None
        if fallback in (None, ""):
            return None
        return str(fallback)
    except Exception:
        return None


def _query_flag(name: str, default: bool = False) -> bool:
    value = str(_get_query_param(name) or "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _normalize_subject_label(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if text in {"company", "organization", "organisation", "legalentity"}:
        return "Company"
    return "Person"


def _resolve_existing_subject(subject_name: str, subject_label: str) -> dict[str, str] | None:
    _, results = safe_neo4j_call("Search subject", search_entities, [], client, subject_name)
    normalized_name = subject_name.strip().casefold()
    for row in results:
        row_name = str(row.get("name") or "").strip().casefold()
        if row.get("label") == subject_label and row_name == normalized_name:
            return {
                "label": str(row["label"]),
                "id": str(row["id"]),
                "name": str(row["name"]),
            }
    for row in results:
        if row.get("label") == subject_label and row.get("id") and row.get("name"):
            return {
                "label": str(row["label"]),
                "id": str(row["id"]),
                "name": str(row["name"]),
            }
    return None


def _create_intake_subject(
    subject_name: str,
    subject_label: str,
    *,
    crm_subject_source: str = "",
    crm_subject_id: str = "",
) -> dict[str, str]:
    entity_id = f"{subject_label.lower()}-{uuid4()}"
    props: dict[str, object] = {"id": entity_id}
    if subject_label == "Person":
        props["full_name"] = subject_name
    else:
        props["name"] = subject_name
    if crm_subject_source:
        props["crm_subject_source"] = crm_subject_source
    if crm_subject_id:
        props["crm_subject_id"] = crm_subject_id
    batch = IngestionBatch(
        source="crm_launch",
        entities=[Entity(label=subject_label, properties=props)],
        relationships=[],
    )
    apply_batch(client, batch)
    return {"label": subject_label, "id": entity_id, "name": subject_name}


def _bootstrap_launch_context() -> dict[str, object]:
    subject_name = str(_get_query_param("subject") or "").strip()
    if not subject_name:
        return {}

    context = {
        "subject_name": subject_name,
        "subject_label": _normalize_subject_label(_get_query_param("subject_type")),
        "start_mode": str(_get_query_param("start_mode") or "analysis")
        .strip()
        .replace("_", " ")
        .title(),
        "use_wikidata": _query_flag("use_wikidata", True),
        "use_opensanctions": _query_flag("use_opensanctions", True),
        "use_news": _query_flag("use_news", False),
        "autorun": _query_flag("autorun", False),
        "opensanctions_dataset": (
            str(_get_query_param("opensanctions_dataset") or "").strip()
            or settings.opensanctions_dataset
        ),
        "crm_subject_source": str(_get_query_param("crm_subject_source") or "").strip(),
        "crm_subject_id": str(_get_query_param("crm_subject_id") or "").strip(),
    }
    signature = json.dumps(context, sort_keys=True)
    if st.session_state.get("dd_launch_signature") == signature:
        return context

    st.session_state["dd_search_term"] = context["subject_name"]
    st.session_state["dd_dossier_src_wikidata"] = bool(context["use_wikidata"])
    st.session_state["dd_dossier_src_opensanctions"] = bool(context["use_opensanctions"])
    st.session_state["dd_dossier_src_newsapi"] = bool(context["use_news"])
    st.session_state["dd_opensanctions_mode"] = "Match"
    st.session_state["dd_cfg_opensanctions_dataset"] = context["opensanctions_dataset"]

    selected = _resolve_existing_subject(
        str(context["subject_name"]), str(context["subject_label"])
    )
    if selected is None:
        ok, selected = safe_neo4j_call(
            "Create intake subject",
            _create_intake_subject,
            None,
            str(context["subject_name"]),
            str(context["subject_label"]),
            crm_subject_source=str(context["crm_subject_source"]),
            crm_subject_id=str(context["crm_subject_id"]),
        )
        if not ok:
            selected = None
    if selected:
        st.session_state["dd_selected_entity_id"] = selected["id"]
        st.session_state["dd_selected_entity_label"] = selected["label"]
        st.session_state["dd_selected_entity_name"] = selected["name"]

    st.session_state["dd_launch_signature"] = signature
    st.session_state["dd_launch_context"] = context
    st.session_state["dd_autorun_pending_signature"] = signature if context["autorun"] else ""
    return context


launch_context = _bootstrap_launch_context()
if launch_context:
    enabled_sources = []
    if launch_context.get("use_wikidata"):
        enabled_sources.append("Wikidata")
    if launch_context.get("use_opensanctions"):
        enabled_sources.append(
            f"OpenSanctions ({launch_context.get('opensanctions_dataset')})"
        )
    if launch_context.get("use_news"):
        enabled_sources.append("News/Web")
    source_text = ", ".join(enabled_sources) if enabled_sources else "no sources selected"
    st.info(
        f"Launch context loaded for {launch_context['subject_name']} "
        f"({launch_context['subject_label']}) via {launch_context['start_mode']}. "
        f"Selected sources: {source_text}."
    )


with st.sidebar:
    st.header("Setup")
    st.subheader("Connection")
    st.session_state.setdefault("neo4j_uri", settings.neo4j_uri)
    st.session_state.setdefault("neo4j_user", settings.neo4j_user)
    st.session_state.setdefault("neo4j_password", settings.neo4j_password)
    st.session_state.setdefault("neo4j_database", settings.neo4j_database)

    st.text_input("URI", key="neo4j_uri")
    st.text_input("User", key="neo4j_user")
    st.text_input("Password", key="neo4j_password", type="password")
    st.text_input("Database", key="neo4j_database")

    if st.button("Apply Connection Settings"):
        st.cache_resource.clear()
        st.experimental_rerun()

    if st.button("Initialize Neo4j Schema"):
        ok, _ = safe_neo4j_call("Initialize schema", initialize_schema, None, client)
        if ok:
            st.success("Schema initialized.")

    if st.button("Seed Sample Data"):
        ok, _ = safe_neo4j_call("Seed sample data", seed_sample_data, None, client)
        if ok:
            st.success("Sample data added.")

    if st.button("Populate Demo Graph"):
        ok, _ = safe_neo4j_call("Populate demo graph", seed_demo_graph, None, client)
        if ok:
            st.success("Demo graph populated.")

    if st.button("Test Neo4j Connection"):
        ok, _ = safe_neo4j_call("Connection test", client.run, [], "RETURN 1 AS ok")
        if ok:
            st.success("Neo4j connection OK.")

    st.divider()
    st.header("Create Entity")
    create_label = st.selectbox("Entity type", ["Person", "Company"])
    create_name = st.text_input("Entity name")
    if st.button("Create"):
        if create_name.strip():
            entity_id = f"{create_label.lower()}-{uuid4()}"
            props = {"id": entity_id}
            if create_label == "Person":
                props["full_name"] = create_name.strip()
            else:
                props["name"] = create_name.strip()

            batch = IngestionBatch(
                source="manual",
                entities=[Entity(label=create_label, properties=props)],
                relationships=[],
            )
            ok, _ = safe_neo4j_call("Create entity", apply_batch, None, client, batch)
            if ok:
                st.success(f"{create_label} created.")
        else:
            st.warning("Enter a name before creating.")

    st.divider()
    st.header("Weekly Monitoring")
    if st.button("Run Weekly Job"):
        ok, _ = safe_neo4j_call(
            "Weekly monitoring", run_weekly_monitoring, None, client, settings
        )
        if ok:
            st.success("Weekly monitoring run completed.")


st.subheader("Search")
st.session_state.setdefault("dd_search_term", "")
search_term = st.text_input("Search for a person or company", key="dd_search_term").strip()

results = []
if search_term.strip():
    _, results = safe_neo4j_call(
        "Search", search_entities, [], client, search_term.strip()
    )

selected = None
selected_entity_id = str(st.session_state.get("dd_selected_entity_id") or "").strip()
selected_entity_label = str(st.session_state.get("dd_selected_entity_label") or "").strip()
if results:
    display_results = [r for r in results if r.get("name")]
    if display_results:
        label_to_display = [
            f'{r["label"]}: {r["name"]} ({r["id"]})' for r in display_results
        ]
        selected_index = 0
        for index, row in enumerate(display_results):
            if row["id"] == selected_entity_id and row["label"] == selected_entity_label:
                selected_index = index
                break
        selection = st.selectbox("Results", label_to_display, index=selected_index)
        selected = display_results[label_to_display.index(selection)]
        st.session_state["dd_selected_entity_id"] = selected["id"]
        st.session_state["dd_selected_entity_label"] = selected["label"]
        st.session_state["dd_selected_entity_name"] = selected["name"]
elif selected_entity_id and selected_entity_label:
    _, selected_entity = safe_neo4j_call(
        "Load selected entity", get_entity, {}, client, selected_entity_label, selected_entity_id
    )
    if selected_entity:
        selected = {
            "label": selected_entity_label,
            "id": selected_entity_id,
            "name": (
                selected_entity.get("full_name")
                or selected_entity.get("name")
                or st.session_state.get("dd_selected_entity_name")
                or selected_entity_id
            ),
        }

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Entity Overview")
    if selected:
        _, entity = safe_neo4j_call(
            "Load entity", get_entity, {}, client, selected["label"], selected["id"]
        )
        if entity:
            st.json(entity)

        st.subheader("Connections")
        _, neighbors = safe_neo4j_call(
            "Load connections", get_neighbors, [], client, selected["label"], selected["id"]
        )
        if neighbors:
            graph_html = build_graph_html(
                center_id=selected["id"],
                center_label=selected["label"],
                center_name=selected["name"],
                neighbors=neighbors,
            )
            st.components.v1.html(graph_html, height=640, scrolling=True)
            st.dataframe(neighbors, use_container_width=True)
        else:
            st.info("No connections found yet.")
    else:
        st.info("Search and select an entity to view details.")

with col_right:
    st.subheader("Risk View")
    if selected:
        _, risky = safe_neo4j_call(
            "Load risk view",
            get_risky_neighbors,
            [],
            client,
            selected["label"],
            selected["id"],
        )
        if risky:
            st.dataframe(risky, use_container_width=True)
        else:
            st.caption("No risky nodes within 2 hops.")

        st.subheader("Enrichment")
        st.session_state.setdefault("dd_opensanctions_mode", "Search")
        opensanctions_mode = st.selectbox(
            "OpenSanctions mode", ["Search", "Match"], key="dd_opensanctions_mode"
        )
        st.session_state.setdefault(
            "dd_cfg_opensanctions_dataset", settings.opensanctions_dataset
        )
        opensanctions_dataset = (
            str(st.session_state.get("dd_cfg_opensanctions_dataset") or "").strip()
            or settings.opensanctions_dataset
        )
        georgia_profiles: list[dict[str, object]] = []
        georgia_catalog_error = None
        try:
            georgia_profiles = load_georgia_profiles(settings.opensanctions_api_key)
        except Exception as exc:
            georgia_catalog_error = str(exc)

        if georgia_profiles:
            st.markdown("##### OpenSanctions presets (Georgia context)")
            preset_labels = []
            label_to_dataset: dict[str, str] = {}
            for item in georgia_profiles:
                name = str(item.get("name") or "").strip()
                title = str(item.get("title") or name).strip()
                group = str(item.get("group") or "")
                entities = int(item.get("entity_count") or 0)
                if not name:
                    continue
                label = f"{name} — {title} [{group}] ({entities:,})"
                preset_labels.append(label)
                label_to_dataset[label] = name

            dataset_names = list(label_to_dataset.values())
            custom_label = "Custom dataset (manual)"
            options = preset_labels + [custom_label]
            if opensanctions_dataset in dataset_names:
                default_index = dataset_names.index(opensanctions_dataset)
            else:
                try:
                    default_index = dataset_names.index("ge_declarations")
                except ValueError:
                    default_index = len(options) - 1

            selected_preset = st.selectbox(
                "Dataset preset",
                options=options,
                index=default_index,
                help="Georgia core datasets are prioritized for local political due diligence.",
            )
            if selected_preset != custom_label:
                opensanctions_dataset = label_to_dataset[selected_preset]
            else:
                opensanctions_dataset = st.text_input(
                    "OpenSanctions dataset",
                    value=opensanctions_dataset,
                    help="Examples: default, sanctions, wd_peps, ge_declarations, ge_ot_list",
                ).strip() or settings.opensanctions_dataset

            with st.expander("Georgia dataset snapshot (from OpenSanctions catalog)", expanded=False):
                st.dataframe(georgia_profiles, use_container_width=True)
        else:
            if georgia_catalog_error:
                st.caption(f"Could not load OpenSanctions catalog: {georgia_catalog_error}")
            opensanctions_dataset = st.text_input(
                "OpenSanctions dataset",
                value=opensanctions_dataset,
                help="Common values: default, sanctions, wd_peps, ge_declarations, ge_ot_list",
            )
        st.session_state["dd_cfg_opensanctions_dataset"] = opensanctions_dataset

        _, entity_snapshot = safe_neo4j_call(
            "Load entity", get_entity, {}, client, selected["label"], selected["id"]
        )
        entity_snapshot = entity_snapshot or {}

        def _run_opensanctions_enrichment(dataset_name: str, entity: dict[str, object]):
            matches: list[dict[str, object]] = []
            if opensanctions_mode == "Match":
                properties: dict[str, list[str]] = {"name": [selected["name"]]}
                aliases = entity.get("aliases") or []
                if isinstance(aliases, list) and aliases:
                    properties["name"].extend([str(alias) for alias in aliases])
                birth_date = entity.get("birth_date")
                if birth_date:
                    properties["birthDate"] = [str(birth_date)]
                nationality = entity.get("nationality")
                if nationality:
                    properties["nationality"] = [str(nationality)]

                schema = "Person" if selected["label"] == "Person" else "Company"
                batch, matches = fetch_opensanctions_match(
                    selected["name"],
                    api_key=settings.opensanctions_api_key,
                    dataset=dataset_name,
                    schema=schema,
                    properties=properties,
                    target_label=selected["label"],
                    target_id=selected["id"],
                )
            else:
                batch, matches = fetch_opensanctions_search(
                    selected["name"],
                    api_key=settings.opensanctions_api_key,
                    dataset=dataset_name,
                    target_label=selected["label"],
                    target_id=selected["id"],
                )
            ok, _ = safe_neo4j_call("OpenSanctions enrichment", apply_batch, None, client, batch)
            return ok, batch, matches

        def _attach_mentions(article_batch: IngestionBatch) -> IngestionBatch:
            relationships: list[Relationship] = []
            for article_entity in article_batch.entities:
                article_id = str(article_entity.properties.get("id") or "").strip()
                if not article_id:
                    continue
                rel_props: dict[str, object] = {}
                article_source = article_entity.properties.get("source")
                if article_source:
                    rel_props["source"] = article_source
                published_date = article_entity.properties.get("published_date")
                if published_date:
                    rel_props["published_date"] = published_date
                relationships.append(
                    Relationship(
                        source_label=selected["label"],
                        source_id=selected["id"],
                        rel_type="MENTIONED_IN",
                        target_label="NewsArticle",
                        target_id=article_id,
                        properties=rel_props,
                    )
                )
            return IngestionBatch(
                source=article_batch.source,
                entities=article_batch.entities,
                relationships=relationships,
            )

        def _run_launch_selected_sources() -> list[dict[str, object]]:
            source_runs: list[dict[str, object]] = []

            if st.session_state.get("dd_dossier_src_wikidata"):
                try:
                    batch = fetch_wikidata(
                        selected["name"],
                        target_label=selected["label"],
                        target_id=selected["id"],
                    )
                    ok, _ = safe_neo4j_call(
                        "Wikidata enrichment", apply_batch, None, client, batch
                    )
                    source_runs.append(
                        {
                            "source": "wikidata",
                            "ok": bool(ok),
                            "items": len(batch.entities),
                            "detail": "profile + relationship graph",
                        }
                    )
                except Exception as exc:
                    source_runs.append(
                        {
                            "source": "wikidata",
                            "ok": False,
                            "items": 0,
                            "detail": str(exc),
                        }
                    )

            if st.session_state.get("dd_dossier_src_opensanctions"):
                if not settings.opensanctions_api_key:
                    source_runs.append(
                        {
                            "source": f"opensanctions:{opensanctions_dataset}",
                            "ok": False,
                            "items": 0,
                            "detail": "missing OPENSANCTIONS_API_KEY",
                        }
                    )
                else:
                    try:
                        ok, batch, matches = _run_opensanctions_enrichment(
                            opensanctions_dataset, entity_snapshot
                        )
                        source_runs.append(
                            {
                                "source": f"opensanctions:{opensanctions_dataset}",
                                "ok": bool(ok),
                                "items": len(batch.entities),
                                "detail": f"matches={len(matches)}",
                            }
                        )
                    except Exception as exc:
                        source_runs.append(
                            {
                                "source": f"opensanctions:{opensanctions_dataset}",
                                "ok": False,
                                "items": 0,
                                "detail": str(exc),
                            }
                        )

            if st.session_state.get("dd_dossier_src_newsapi"):
                if not settings.news_api_key:
                    source_runs.append(
                        {
                            "source": "newsapi",
                            "ok": False,
                            "items": 0,
                            "detail": "missing NEWS_API_KEY",
                        }
                    )
                else:
                    try:
                        batch = fetch_news_articles(settings.news_api_key, selected["name"])
                        batch = _attach_mentions(batch)
                        ok, _ = safe_neo4j_call(
                            "News ingestion", apply_batch, None, client, batch
                        )
                        source_runs.append(
                            {
                                "source": "newsapi",
                                "ok": bool(ok),
                                "items": len(batch.entities),
                                "detail": "recent headlines",
                            }
                        )
                    except Exception as exc:
                        source_runs.append(
                            {
                                "source": "newsapi",
                                "ok": False,
                                "items": 0,
                                "detail": str(exc),
                            }
                        )
            return source_runs

        pending_autorun_signature = str(
            st.session_state.get("dd_autorun_pending_signature") or ""
        ).strip()
        launch_signature = str(st.session_state.get("dd_launch_signature") or "").strip()
        if pending_autorun_signature and pending_autorun_signature == launch_signature:
            with st.spinner("Running launch-selected sources..."):
                st.session_state["dd_last_autorun_source_runs"] = _run_launch_selected_sources()
                st.session_state["dd_last_autorun_subject_id"] = selected["id"]
                st.session_state["dd_last_autorun_dataset"] = opensanctions_dataset
                st.session_state["dd_autorun_pending_signature"] = ""
            st.rerun()

        latest_autorun_runs = st.session_state.get("dd_last_autorun_source_runs")
        latest_autorun_subject_id = str(
            st.session_state.get("dd_last_autorun_subject_id") or ""
        ).strip()
        if isinstance(latest_autorun_runs, list) and latest_autorun_subject_id == selected["id"]:
            st.caption("Latest launch-triggered enrichment")
            st.dataframe(latest_autorun_runs, use_container_width=True)

        st.subheader("Dossier Generator")
        st.caption(
            "Generate a consolidated dossier from multiple public databases in one run."
        )
        source_cols = st.columns(2)
        with source_cols[0]:
            use_wikidata = st.checkbox(
                "Wikidata", value=True, key="dd_dossier_src_wikidata"
            )
            use_wikipedia = st.checkbox(
                "Wikipedia profile", value=True, key="dd_dossier_src_wikipedia"
            )
            use_opensanctions = st.checkbox(
                "OpenSanctions",
                value=True,
                key="dd_dossier_src_opensanctions",
            )
        with source_cols[1]:
            use_newsapi = st.checkbox(
                "NewsAPI (recent headlines)",
                value=bool(settings.news_api_key),
                key="dd_dossier_src_newsapi",
            )
            use_gdelt = st.checkbox(
                "GDELT (global media)",
                value=True,
                key="dd_dossier_src_gdelt",
            )
            use_georgia_sweep = st.checkbox(
                "OpenSanctions Georgia sweep",
                value=False,
                key="dd_dossier_src_georgia_sweep",
            )

        if st.button("Generate Dossier (all selected sources)", type="primary"):
            source_runs: list[dict[str, object]] = []
            _, working_entity = safe_neo4j_call(
                "Load entity", get_entity, {}, client, selected["label"], selected["id"]
            )
            working_entity = working_entity or entity_snapshot

            if use_wikidata:
                try:
                    batch = fetch_wikidata(
                        selected["name"],
                        target_label=selected["label"],
                        target_id=selected["id"],
                    )
                    ok, _ = safe_neo4j_call(
                        "Wikidata enrichment", apply_batch, None, client, batch
                    )
                    source_runs.append(
                        {
                            "source": "wikidata",
                            "ok": bool(ok),
                            "items": len(batch.entities),
                            "detail": "profile + relationship graph",
                        }
                    )
                except Exception as exc:
                    source_runs.append(
                        {
                            "source": "wikidata",
                            "ok": False,
                            "items": 0,
                            "detail": str(exc),
                        }
                    )

            if use_wikipedia:
                try:
                    batch = fetch_wikipedia_profile(
                        selected["name"],
                        target_label=selected["label"],
                        target_id=selected["id"],
                    )
                    ok, _ = safe_neo4j_call(
                        "Wikipedia enrichment", apply_batch, None, client, batch
                    )
                    source_runs.append(
                        {
                            "source": "wikipedia",
                            "ok": bool(ok),
                            "items": len(batch.entities),
                            "detail": "encyclopedia profile",
                        }
                    )
                except Exception as exc:
                    source_runs.append(
                        {
                            "source": "wikipedia",
                            "ok": False,
                            "items": 0,
                            "detail": str(exc),
                        }
                    )

            if use_opensanctions:
                if not settings.opensanctions_api_key:
                    source_runs.append(
                        {
                            "source": "opensanctions",
                            "ok": False,
                            "items": 0,
                            "detail": "missing OPENSANCTIONS_API_KEY",
                        }
                    )
                elif use_georgia_sweep:
                    sweep_datasets = [
                        str(item.get("name") or "").strip()
                        for item in georgia_profiles
                        if str(item.get("group") or "") == "Georgia core"
                    ]
                    sweep_datasets = [name for name in sweep_datasets if name]
                    if not sweep_datasets:
                        sweep_datasets = [
                            "ge_declarations",
                            "ge_ot_list",
                            "ext_ge_company_registry",
                        ]
                    for dataset_name in sweep_datasets:
                        try:
                            ok, batch, matches = _run_opensanctions_enrichment(
                                dataset_name, working_entity
                            )
                            source_runs.append(
                                {
                                    "source": f"opensanctions:{dataset_name}",
                                    "ok": bool(ok),
                                    "items": len(batch.entities),
                                    "detail": f"matches={len(matches)}",
                                }
                            )
                        except Exception as exc:
                            source_runs.append(
                                {
                                    "source": f"opensanctions:{dataset_name}",
                                    "ok": False,
                                    "items": 0,
                                    "detail": str(exc),
                                }
                            )
                else:
                    try:
                        ok, batch, matches = _run_opensanctions_enrichment(
                            opensanctions_dataset, working_entity
                        )
                        source_runs.append(
                            {
                                "source": f"opensanctions:{opensanctions_dataset}",
                                "ok": bool(ok),
                                "items": len(batch.entities),
                                "detail": f"matches={len(matches)}",
                            }
                        )
                    except Exception as exc:
                        source_runs.append(
                            {
                                "source": f"opensanctions:{opensanctions_dataset}",
                                "ok": False,
                                "items": 0,
                                "detail": str(exc),
                            }
                        )

            if use_newsapi:
                if not settings.news_api_key:
                    source_runs.append(
                        {
                            "source": "newsapi",
                            "ok": False,
                            "items": 0,
                            "detail": "missing NEWS_API_KEY",
                        }
                    )
                else:
                    try:
                        news_batch = fetch_news_articles(
                            settings.news_api_key, selected["name"]
                        )
                        news_batch = _attach_mentions(news_batch)
                        ok, _ = safe_neo4j_call(
                            "News ingestion", apply_batch, None, client, news_batch
                        )
                        source_runs.append(
                            {
                                "source": "newsapi",
                                "ok": bool(ok),
                                "items": len(news_batch.entities),
                                "detail": "recent headlines",
                            }
                        )
                    except Exception as exc:
                        source_runs.append(
                            {
                                "source": "newsapi",
                                "ok": False,
                                "items": 0,
                                "detail": str(exc),
                            }
                        )

            if use_gdelt:
                try:
                    gdelt_batch = fetch_gdelt_articles(selected["name"])
                    gdelt_batch = _attach_mentions(gdelt_batch)
                    ok, _ = safe_neo4j_call(
                        "GDELT ingestion", apply_batch, None, client, gdelt_batch
                    )
                    source_runs.append(
                        {
                            "source": "gdelt",
                            "ok": bool(ok),
                            "items": len(gdelt_batch.entities),
                            "detail": "global media index",
                        }
                    )
                except Exception as exc:
                    source_runs.append(
                        {
                            "source": "gdelt",
                            "ok": False,
                            "items": 0,
                            "detail": str(exc),
                        }
                    )

            _, latest_entity = safe_neo4j_call(
                "Load entity", get_entity, {}, client, selected["label"], selected["id"]
            )
            latest_entity = latest_entity or {}
            _, latest_neighbors = safe_neo4j_call(
                "Load connections", get_neighbors, [], client, selected["label"], selected["id"]
            )
            _, latest_risky = safe_neo4j_call(
                "Load risk view",
                get_risky_neighbors,
                [],
                client,
                selected["label"],
                selected["id"],
            )
            snapshot = build_dossier_snapshot(
                subject={
                    "label": selected["label"],
                    "id": selected["id"],
                    "name": selected["name"],
                },
                entity=latest_entity,
                neighbors=latest_neighbors,
                risky=latest_risky,
                source_runs=source_runs,
            )
            markdown_text = dossier_markdown(snapshot)
            st.session_state["dd_last_dossier_snapshot"] = snapshot
            st.session_state["dd_last_dossier_markdown"] = markdown_text
            st.success("Dossier generation finished.")
            st.dataframe(source_runs, use_container_width=True)

        dossier_snapshot = st.session_state.get("dd_last_dossier_snapshot")
        if isinstance(dossier_snapshot, dict):
            dossier_subject = dossier_snapshot.get("subject") or {}
            if dossier_subject.get("id") == selected["id"]:
                markdown_text = str(
                    st.session_state.get("dd_last_dossier_markdown") or ""
                )
                with st.expander("Latest dossier summary", expanded=True):
                    st.markdown(markdown_text)
                    safe_subject_id = selected["id"].replace(":", "_").replace("/", "_")
                    st.download_button(
                        "Download dossier (Markdown)",
                        data=markdown_text.encode("utf-8"),
                        file_name=f"dossier-{safe_subject_id}.md",
                        mime="text/markdown",
                    )
                    st.download_button(
                        "Download dossier (JSON)",
                        data=json.dumps(
                            dossier_snapshot, ensure_ascii=False, indent=2
                        ).encode("utf-8"),
                        file_name=f"dossier-{safe_subject_id}.json",
                        mime="application/json",
                    )

        st.markdown("---")
        st.caption("Manual source actions")

        if st.button("Enrich from Wikidata"):
            try:
                batch = fetch_wikidata(
                    selected["name"],
                    target_label=selected["label"],
                    target_id=selected["id"],
                )
            except HTTPError as exc:
                st.error(f"Wikidata request failed: {exc}")
            else:
                ok, _ = safe_neo4j_call(
                    "Wikidata enrichment", apply_batch, None, client, batch
                )
                if ok:
                    st.success("Wikidata enrichment applied.")

        if st.button("Enrich from OpenSanctions"):
            if not settings.opensanctions_api_key:
                st.error("Set OPENSANCTIONS_API_KEY in .env to use OpenSanctions.")
            else:
                ok, _, matches = _run_opensanctions_enrichment(
                    opensanctions_dataset, entity_snapshot
                )
                if ok:
                    st.success(f"OpenSanctions enrichment applied (dataset: {opensanctions_dataset}).")
                if matches:
                    st.caption("OpenSanctions matches (top results)")
                    st.dataframe(matches, use_container_width=True)
        if st.button("Run Georgia sweep (core datasets)"):
            if not settings.opensanctions_api_key:
                st.error("Set OPENSANCTIONS_API_KEY in .env to use OpenSanctions.")
            else:
                sweep_datasets = [
                    str(item.get("name") or "").strip()
                    for item in georgia_profiles
                    if str(item.get("group") or "") == "Georgia core"
                ]
                sweep_datasets = [name for name in sweep_datasets if name]
                if not sweep_datasets:
                    sweep_datasets = ["ge_declarations", "ge_ot_list", "ext_ge_company_registry"]
                run_rows = []
                for dataset_name in sweep_datasets:
                    try:
                        ok, batch, matches = _run_opensanctions_enrichment(
                            dataset_name, entity_snapshot
                        )
                        run_rows.append(
                            {
                                "dataset": dataset_name,
                                "ok": bool(ok),
                                "entities": len(batch.entities),
                                "relationships": len(batch.relationships),
                                "matches": len(matches),
                            }
                        )
                    except Exception as exc:
                        run_rows.append(
                            {
                                "dataset": dataset_name,
                                "ok": False,
                                "entities": 0,
                                "relationships": 0,
                                "matches": 0,
                                "error": str(exc),
                            }
                        )
                st.caption("Georgia sweep results")
                st.dataframe(run_rows, use_container_width=True)
                ok_count = sum(1 for row in run_rows if row.get("ok"))
                st.success(f"Georgia sweep completed: {ok_count}/{len(run_rows)} datasets applied.")

        if st.button("Fetch Recent News"):
            batch = fetch_news_articles(settings.news_api_key, selected["name"])
            batch = _attach_mentions(batch)
            ok, _ = safe_neo4j_call("News ingestion", apply_batch, None, client, batch)
            if ok:
                st.success("News articles ingested.")
        if st.button("Fetch GDELT Global News"):
            batch = fetch_gdelt_articles(selected["name"])
            batch = _attach_mentions(batch)
            ok, _ = safe_neo4j_call("GDELT ingestion", apply_batch, None, client, batch)
            if ok:
                st.success("GDELT articles ingested.")
        st.subheader("Report")
        if st.button("Generate PDF Report"):
            _, entity = safe_neo4j_call(
                "Load entity", get_entity, {}, client, selected["label"], selected["id"]
            )
            entity = entity or {}
            _, neighbors = safe_neo4j_call(
                "Load connections", get_neighbors, [], client, selected["label"], selected["id"]
            )
            _, risky = safe_neo4j_call(
                "Load risk view",
                get_risky_neighbors,
                [],
                client,
                selected["label"],
                selected["id"],
            )

            profile_lines = [
                f"Name: {selected['name']}",
                f"Type: {selected['label']}",
                f"ID: {selected['id']}",
            ]
            summary = entity.get("summary")
            if summary:
                profile_lines.append(f"Summary: {summary}")
            nationality = entity.get("nationality")
            if nationality:
                profile_lines.append(f"Nationality: {nationality}")
            jurisdiction = entity.get("jurisdiction")
            if jurisdiction:
                profile_lines.append(f"Jurisdiction: {jurisdiction}")

            connection_lines = [
                f"{row['rel']} -> {row['target_name']} ({row['target_label']})"
                for row in neighbors
            ][:50]
            risk_lines = [f"{row['name']} ({row['label']})" for row in risky][:50]
            sources = entity.get("source_refs") or []
            source_lines = [str(source) for source in sources][:50]

            safe_id = selected["id"].replace(":", "_").replace("/", "_")
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            output_path = Path("reports") / f"report-{safe_id}-{timestamp}.pdf"

            try:
                generate_pdf_report(
                    output_path,
                    title=f"Due Diligence Report: {selected['name']}",
                    sections=[
                        ("Entity Profile", profile_lines),
                        ("Connections", connection_lines),
                        ("Risk Indicators", risk_lines),
                        ("Sources", source_lines),
                    ],
                )
            except RuntimeError as exc:
                st.error(str(exc))
            else:
                report_bytes = output_path.read_bytes()
                st.download_button(
                    label="Download report",
                    data=report_bytes,
                    file_name=output_path.name,
                    mime="application/pdf",
                )
    else:
        st.caption("Select an entity to enable enrichment.")
