from __future__ import annotations

from typing import Any

import requests

from app.ingestion.models import Entity, IngestionBatch, Relationship


OPENSANCTIONS_API = "https://api.opensanctions.org"
PERSON_SCHEMAS = {"Person"}
COMPANY_SCHEMAS = {"Company", "Organization", "LegalEntity"}
OPENSANCTIONS_SOURCE_ID = "source:opensanctions"
OPENSANCTIONS_SOURCE_NAME = "OpenSanctions"
DATASET_ID_PREFIX = "opensanctions:dataset:"


def fetch_opensanctions_search(
    entity_name: str,
    api_key: str | None,
    dataset: str = "default",
    target_label: str | None = None,
    target_id: str | None = None,
    limit: int = 5,
) -> tuple[IngestionBatch, list[dict[str, Any]]]:
    if not api_key:
        return IngestionBatch(source="opensanctions", entities=[], relationships=[]), []

    session = _build_session(api_key)
    response = session.get(
        f"{OPENSANCTIONS_API}/search/{dataset}",
        params={"q": entity_name, "limit": limit},
        timeout=20,
    )
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    results = data.get("results") or []
    if not results:
        return IngestionBatch(source="opensanctions", entities=[], relationships=[]), []

    return _build_batch_from_results(
        results=results,
        session=session,
        target_label=target_label,
        target_id=target_id,
    )


def fetch_opensanctions_match(
    entity_name: str,
    api_key: str | None,
    dataset: str = "default",
    schema: str = "Person",
    properties: dict[str, list[str]] | None = None,
    target_label: str | None = None,
    target_id: str | None = None,
    limit: int = 5,
) -> tuple[IngestionBatch, list[dict[str, Any]]]:
    if not api_key:
        return IngestionBatch(source="opensanctions", entities=[], relationships=[]), []

    session = _build_session(api_key)
    query: dict[str, Any] = {
        "schema": schema,
        "properties": properties or {"name": [entity_name]},
    }
    request_body = {"queries": {"query": query}}
    response = session.post(
        f"{OPENSANCTIONS_API}/match/{dataset}",
        json=request_body,
        timeout=30,
    )
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    results = (
        (data.get("responses") or {})
        .get("query", {})
        .get("results", [])
    )
    if not results:
        return IngestionBatch(source="opensanctions", entities=[], relationships=[]), []

    trimmed_results = results[:limit]
    return _build_batch_from_results(
        results=trimmed_results,
        session=session,
        target_label=target_label,
        target_id=target_id,
    )


def _build_batch_from_results(
    results: list[dict[str, Any]],
    session: requests.Session,
    target_label: str | None,
    target_id: str | None,
) -> tuple[IngestionBatch, list[dict[str, Any]]]:
    entities: list[Entity] = [_build_opensanctions_source_entity()]
    relationships: list[Relationship] = []

    display_rows = _build_match_display_rows(results)
    top_result = results[0]
    top_id = top_result.get("id")
    if top_id:
        detail = _fetch_entity_detail(top_id, session)
    else:
        detail = None

    if target_id and target_label and detail:
        entity = _build_entity_from_detail(
            detail,
            entity_id=target_id,
            label_override=target_label,
        )
        entities.append(entity)
        dataset_entities, dataset_relationships = _build_dataset_relationships(
            entity_id=target_id,
            entity_label=target_label,
            datasets=detail.get("datasets") or top_result.get("datasets") or [],
            topics=detail.get("topics") or top_result.get("topics") or [],
        )
        entities.extend(dataset_entities)
        relationships.extend(dataset_relationships)
    else:
        for result in results:
            result_id = result.get("id")
            detail = _fetch_entity_detail(result_id, session) if result_id else None
            entity = _build_entity_from_detail(detail or result)
            entities.append(entity)
            dataset_entities, dataset_relationships = _build_dataset_relationships(
                entity_id=entity.properties["id"],
                entity_label=entity.label,
                datasets=(detail or result).get("datasets") or [],
                topics=(detail or result).get("topics") or [],
            )
            entities.extend(dataset_entities)
            relationships.extend(dataset_relationships)

    return (
        IngestionBatch(
            source="opensanctions",
            entities=_unique_entities(entities),
            relationships=relationships,
        ),
        display_rows,
    )


def _build_entity_from_detail(
    result: dict[str, Any], entity_id: str | None = None, label_override: str | None = None
) -> Entity:
    schema = result.get("schema")
    label = label_override or _map_schema(schema)
    entity_id = entity_id or f"opensanctions:{result.get('id')}"
    caption = result.get("caption") or result.get("id")
    properties = result.get("properties") or {}
    topics = result.get("topics") or []
    datasets = result.get("datasets") or []

    props: dict[str, Any] = {"id": entity_id}
    if label == "Person":
        props["full_name"] = caption
        aliases = _get_values(properties, ["alias", "name", "weakAlias"])
        if aliases:
            props["aliases"] = aliases
        birth_date = _first_value(properties, ["birthDate", "birthDateFrom"])
        if birth_date:
            props["birth_date"] = birth_date
        nationality = _first_value(properties, ["nationality", "citizenship", "country"])
        if nationality:
            props["nationality"] = nationality
    else:
        props["name"] = caption
        aliases = _get_values(properties, ["alias", "name", "weakAlias"])
        if aliases:
            props["aliases"] = aliases
        jurisdiction = _first_value(properties, ["jurisdiction", "country"])
        if jurisdiction:
            props["jurisdiction"] = jurisdiction
        registration_id = _first_value(
            properties, ["registrationNumber", "incorporationNumber", "taxNumber"]
        )
        if registration_id:
            props["registration_id"] = registration_id

    if topics:
        props["topics"] = topics
    if datasets:
        props["datasets"] = datasets

    result_id = result.get("id")
    if result_id:
        props["source_refs"] = [f"https://www.opensanctions.org/entities/{result_id}"]
    return Entity(label=label, properties=props)


def _build_opensanctions_source_entity() -> Entity:
    return Entity(
        label="Source",
        properties={
            "id": OPENSANCTIONS_SOURCE_ID,
            "name": OPENSANCTIONS_SOURCE_NAME,
            "type": "registry",
        },
    )


def _build_dataset_relationships(
    entity_id: str,
    entity_label: str,
    datasets: list[str],
    topics: list[str],
) -> tuple[list[Entity], list[Relationship]]:
    if not datasets and not topics:
        return [], []

    dataset_entities: list[Entity] = []
    relationships: list[Relationship] = []
    classification = _classify_topics(topics)

    for dataset in datasets:
        dataset_id = f"{DATASET_ID_PREFIX}{dataset}"
        dataset_entities.append(
            Entity(
                label="Dataset",
                properties={
                    "id": dataset_id,
                    "name": dataset,
                    "source": OPENSANCTIONS_SOURCE_NAME,
                    "url": f"https://www.opensanctions.org/datasets/{dataset}/",
                },
            )
        )
        rel_props: dict[str, Any] = {"source": "opensanctions"}
        if topics:
            rel_props["topics"] = topics
        if classification:
            rel_props["classification"] = classification

        relationships.append(
            Relationship(
                source_label=entity_label,
                source_id=entity_id,
                rel_type="LISTED_IN",
                target_label="Dataset",
                target_id=dataset_id,
                properties=rel_props,
            )
        )
        relationships.append(
            Relationship(
                source_label="Dataset",
                source_id=dataset_id,
                rel_type="PROVIDED_BY",
                target_label="Source",
                target_id=OPENSANCTIONS_SOURCE_ID,
                properties={"source": "opensanctions"},
            )
        )

    return dataset_entities, relationships


def _map_schema(schema: str | None) -> str:
    if schema in PERSON_SCHEMAS:
        return "Person"
    if schema in COMPANY_SCHEMAS:
        return "Company"
    return "Company"


def _build_session(api_key: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({"Authorization": f"ApiKey {api_key}"})
    return session


def _fetch_entity_detail(entity_id: str, session: requests.Session) -> dict[str, Any]:
    response = session.get(f"{OPENSANCTIONS_API}/entities/{entity_id}", timeout=20)
    response.raise_for_status()
    return response.json()


def _build_match_display_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        rows.append(
            {
                "id": result.get("id"),
                "caption": result.get("caption"),
                "schema": result.get("schema"),
                "score": result.get("score"),
                "datasets": result.get("datasets"),
                "topics": result.get("topics"),
            }
        )
    return rows


def _get_values(properties: dict[str, Any], keys: list[str]) -> list[str]:
    values: list[str] = []
    for key in keys:
        data = properties.get(key) or []
        if isinstance(data, list):
            values.extend([str(item) for item in data if item])
        elif data:
            values.append(str(data))
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _first_value(properties: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        values = _get_values(properties, [key])
        if values:
            return values[0]
    return None


def _classify_topics(topics: list[str]) -> str | None:
    lowered = " ".join(topics).lower()
    if "sanction" in lowered or "watchlist" in lowered:
        return "sanction"
    if "pep" in lowered:
        return "pep"
    return None


def _unique_entities(entities: list[Entity]) -> list[Entity]:
    seen: set[tuple[str, str]] = set()
    unique: list[Entity] = []
    for entity in entities:
        entity_id = str(entity.properties.get("id") or "")
        key = (entity.label, entity_id)
        if not entity_id or key in seen:
            continue
        seen.add(key)
        unique.append(entity)
    return unique


def fetch_opensanctions(entity_name: str) -> IngestionBatch:
    # Placeholder for OpenSanctions integration.
    return IngestionBatch(source="opensanctions", entities=[], relationships=[])
