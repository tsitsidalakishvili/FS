from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv
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
from app.ingestion.news import fetch_news_articles
from app.ingestion.opensanctions import (
    fetch_opensanctions_match,
    get_georgia_dataset_profiles,
    fetch_opensanctions_search,
)
from app.ingestion.wikidata import fetch_wikidata
from app.monitoring.weekly import run_weekly_monitoring
from app.reporting.pdf import generate_pdf_report


load_dotenv()
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
search_term = st.text_input("Search for a person or company")

results = []
if search_term.strip():
    _, results = safe_neo4j_call(
        "Search", search_entities, [], client, search_term.strip()
    )

selected = None
if results:
    display_results = [r for r in results if r.get("name")]
    if display_results:
        label_to_display = [
            f'{r["label"]}: {r["name"]} ({r["id"]})' for r in display_results
        ]
        selection = st.selectbox("Results", label_to_display)
        selected = display_results[label_to_display.index(selection)]

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
        opensanctions_mode = st.selectbox(
            "OpenSanctions mode", ["Search", "Match"], index=0
        )
        opensanctions_dataset = settings.opensanctions_dataset
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
                    value=settings.opensanctions_dataset,
                    help="Examples: default, sanctions, wd_peps, ge_declarations, ge_ot_list",
                ).strip() or settings.opensanctions_dataset

            with st.expander("Georgia dataset snapshot (from OpenSanctions catalog)", expanded=False):
                st.dataframe(georgia_profiles, use_container_width=True)
        else:
            if georgia_catalog_error:
                st.caption(f"Could not load OpenSanctions catalog: {georgia_catalog_error}")
            opensanctions_dataset = st.text_input(
                "OpenSanctions dataset",
                value=settings.opensanctions_dataset,
                help="Common values: default, sanctions, wd_peps, ge_declarations, ge_ot_list",
            )

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
            relationships = []
            for entity in batch.entities:
                relationships.append(
                    Relationship(
                        source_label=selected["label"],
                        source_id=selected["id"],
                        rel_type="MENTIONED_IN",
                        target_label="NewsArticle",
                        target_id=entity.properties.get("id", ""),
                        properties={},
                    )
                )
            batch = IngestionBatch(
                source=batch.source,
                entities=batch.entities,
                relationships=relationships,
            )
            ok, _ = safe_neo4j_call("News ingestion", apply_batch, None, client, batch)
            if ok:
                st.success("News articles ingested.")
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
