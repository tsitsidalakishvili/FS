from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

import requests

from app.ingestion.models import Entity, IngestionBatch, Relationship


WIKIDATA_API = "https://www.wikidata.org/w/api.php"
MAX_RELATED_DEFAULT = 25
USER_AGENT = "GraphDueDiligence/0.1 (local; contact=local)"


def _get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session

LOCATION_INSTANCE_IDS = {
    "Q2221906",  # geographic location
    "Q17334923",  # location
    "Q515",  # city
    "Q486972",  # human settlement
    "Q6256",  # country
    "Q3957",  # town
}

ORGANIZATION_INSTANCE_IDS = {
    "Q43229",  # organization
    "Q783794",  # company
    "Q4830453",  # business
    "Q6881511",  # enterprise
    "Q79913",  # public company
    "Q891723",  # public limited company
}

PERSON_RELATIONSHIPS = [
    ("P26", "SPOUSE_OF", "out", {"Person"}, {}),
    ("P40", "CHILD_OF", "in", {"Person"}, {}),
    ("P22", "CHILD_OF", "out", {"Person"}, {}),
    ("P25", "CHILD_OF", "out", {"Person"}, {}),
    ("P3373", "SIBLING_OF", "out", {"Person"}, {}),
    ("P1038", "RELATIVE_OF", "out", {"Person"}, {"degree": "relative"}),
    ("P108", "WORKS_FOR", "out", {"Company"}, {}),
    ("P551", "RESIDES_IN", "out", {"Location"}, {}),
]

COMPANY_RELATIONSHIPS = [
    ("P127", "OWNED_BY", "out", {"Person", "Company"}, {}),
    ("P112", "FOUNDER_OF", "in", {"Person"}, {}),
    ("P355", "SUBSIDIARY_OF", "out", {"Company"}, {}),
    ("P749", "SUBSIDIARY_OF", "out", {"Company"}, {}),
    ("P169", "DIRECTOR_OF", "in", {"Person"}, {}),
    ("P159", "REGISTERED_IN", "out", {"Location"}, {}),
]


def fetch_wikidata(
    entity_name: str,
    target_label: str | None = None,
    target_id: str | None = None,
    include_relationships: bool = True,
    max_related: int = MAX_RELATED_DEFAULT,
) -> IngestionBatch:
    session = _get_session()
    search = session.get(
        WIKIDATA_API,
        params={
            "action": "wbsearchentities",
            "search": entity_name,
            "language": "en",
            "format": "json",
            "limit": 1,
        },
        timeout=20,
    )
    search.raise_for_status()
    search_data: dict[str, Any] = search.json()
    results = search_data.get("search", [])
    if not results:
        return IngestionBatch(source="wikidata", entities=[], relationships=[])

    qid = results[0].get("id")
    if not qid:
        return IngestionBatch(source="wikidata", entities=[], relationships=[])

    entity = _fetch_entity(qid, session=session)
    if not entity:
        return IngestionBatch(source="wikidata", entities=[], relationships=[])

    label = target_label or _infer_label(entity)
    if not label:
        return IngestionBatch(source="wikidata", entities=[], relationships=[])

    primary_id = target_id or f"wikidata:{qid}"
    primary_entity = _build_primary_entity(
        entity,
        label=label,
        entity_name=entity_name,
        entity_id=primary_id,
        wikidata_id=qid,
    )

    entities = [primary_entity]
    relationships: list[Relationship] = []

    if include_relationships:
        related_entities, relationships = _extract_relationships(
            entity,
            primary_label=label,
            primary_id=primary_id,
            wikidata_id=qid,
            max_related=max_related,
            session=session,
        )
        entities.extend(related_entities)

    return IngestionBatch(
        source="wikidata",
        entities=entities,
        relationships=relationships,
    )


def _fetch_entity(qid: str, session: requests.Session) -> dict[str, Any] | None:
    response = session.get(
        WIKIDATA_API,
        params={
            "action": "wbgetentities",
            "ids": qid,
            "props": "labels|descriptions|aliases|claims",
            "languages": "en",
            "format": "json",
        },
        timeout=20,
    )
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    return (data.get("entities") or {}).get(qid)


def _build_primary_entity(
    entity: dict[str, Any],
    label: str,
    entity_name: str,
    entity_id: str,
    wikidata_id: str,
) -> Entity:
    props: dict[str, Any] = {"id": entity_id}
    summary = _get_lang_value(entity.get("descriptions"), "en")
    aliases = _get_aliases(entity.get("aliases"), "en")
    wikidata_url = f"https://www.wikidata.org/wiki/{wikidata_id}"

    if label == "Person":
        props["full_name"] = _get_lang_value(entity.get("labels"), "en") or entity_name
        if aliases:
            props["aliases"] = aliases
        if summary:
            props["summary"] = summary
        birth_date = _extract_time(entity.get("claims", {}), "P569")
        if birth_date:
            props["birth_date"] = birth_date
        nationality = _extract_entity_label(entity.get("claims", {}), "P27")
        if nationality:
            props["nationality"] = nationality
    elif label == "Company":
        props["name"] = _get_lang_value(entity.get("labels"), "en") or entity_name
        if aliases:
            props["aliases"] = aliases
        if summary:
            props["summary"] = summary
        jurisdiction = (
            _extract_entity_label(entity.get("claims", {}), "P495")
            or _extract_entity_label(entity.get("claims", {}), "P17")
        )
        if jurisdiction:
            props["jurisdiction"] = jurisdiction
    elif label == "Location":
        props["name"] = _get_lang_value(entity.get("labels"), "en") or entity_name
        if summary:
            props["summary"] = summary
        props["type"] = "location"
    else:
        props["name"] = _get_lang_value(entity.get("labels"), "en") or entity_name

    props["wikidata_id"] = wikidata_id
    props["wikidata_url"] = wikidata_url
    props["source_refs"] = [wikidata_url]
    return Entity(label=label, properties=props)


def _build_related_entity(
    entity: dict[str, Any], label: str, entity_id: str, wikidata_id: str
) -> Entity:
    props: dict[str, Any] = {"id": entity_id}
    name = _get_lang_value(entity.get("labels"), "en") or entity_id
    summary = _get_lang_value(entity.get("descriptions"), "en")
    aliases = _get_aliases(entity.get("aliases"), "en")

    if label == "Person":
        props["full_name"] = name
        if aliases:
            props["aliases"] = aliases
    elif label == "Company":
        props["name"] = name
        if aliases:
            props["aliases"] = aliases
    elif label == "Location":
        props["name"] = name
        props["type"] = "location"
    else:
        props["name"] = name

    if summary:
        props["summary"] = summary

    props["wikidata_id"] = wikidata_id
    props["wikidata_url"] = f"https://www.wikidata.org/wiki/{wikidata_id}"
    props["source_refs"] = [props["wikidata_url"]]
    return Entity(label=label, properties=props)


def _extract_relationships(
    entity: dict[str, Any],
    primary_label: str,
    primary_id: str,
    wikidata_id: str,
    max_related: int,
    session: requests.Session,
) -> tuple[list[Entity], list[Relationship]]:
    claims = entity.get("claims", {})
    if primary_label == "Person":
        specs = PERSON_RELATIONSHIPS
    elif primary_label == "Company":
        specs = COMPANY_RELATIONSHIPS
    else:
        return [], []

    related_ids: list[str] = []
    rel_requests: list[tuple[str, str, str, set[str], dict[str, Any], str]] = []
    for prop, rel_type, direction, allowed_labels, base_props in specs:
        ids = _extract_entity_ids(claims, prop)
        for rel_id in ids:
            if rel_id == wikidata_id:
                continue
            related_ids.append(rel_id)
            rel_requests.append(
                (rel_id, rel_type, direction, allowed_labels, base_props, prop)
            )

    if not related_ids:
        return [], []

    unique_ids: list[str] = []
    seen: set[str] = set()
    for rel_id in related_ids:
        if rel_id in seen:
            continue
        seen.add(rel_id)
        unique_ids.append(rel_id)

    limited_ids = unique_ids[:max_related]
    related_entities_data = _fetch_entities(limited_ids, session)

    entities: dict[str, Entity] = {}
    relationships: list[Relationship] = []
    seen_relationships: set[tuple[str, str, str]] = set()

    for rel_id, rel_type, direction, allowed_labels, base_props, prop in rel_requests:
        if rel_id not in related_entities_data or rel_id not in limited_ids:
            continue
        related_entity = related_entities_data[rel_id]
        inferred_label = _classify_entity(related_entity)
        label = inferred_label or (next(iter(allowed_labels)) if allowed_labels else None)
        if not label:
            continue
        if allowed_labels and label not in allowed_labels:
            continue

        entity_id = f"wikidata:{rel_id}"
        if entity_id not in entities:
            entities[entity_id] = _build_related_entity(
                related_entity, label=label, entity_id=entity_id, wikidata_id=rel_id
            )

        rel_props: dict[str, Any] = {"wikidata_prop": prop}
        rel_props.update(base_props)

        if direction == "out":
            source_label = primary_label
            source_id = primary_id
            target_label = label
            target_id = entity_id
        else:
            source_label = label
            source_id = entity_id
            target_label = primary_label
            target_id = primary_id

        rel_key = (source_id, rel_type, target_id)
        if rel_key in seen_relationships:
            continue
        seen_relationships.add(rel_key)
        relationships.append(
            Relationship(
                source_label=source_label,
                source_id=source_id,
                rel_type=rel_type,
                target_label=target_label,
                target_id=target_id,
                properties=rel_props,
            )
        )

    return list(entities.values()), relationships


def _fetch_entities(
    entity_ids: list[str], session: requests.Session
) -> dict[str, dict[str, Any]]:
    entities: dict[str, dict[str, Any]] = {}
    for chunk in _chunked(entity_ids, 50):
        response = session.get(
            WIKIDATA_API,
            params={
                "action": "wbgetentities",
                "ids": "|".join(chunk),
                "props": "labels|descriptions|aliases|claims",
                "languages": "en",
                "format": "json",
            },
            timeout=20,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        entities.update(data.get("entities") or {})
    return entities


def _chunked(items: Iterable[str], size: int) -> Iterable[list[str]]:
    chunk: list[str] = []
    for item in items:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _classify_entity(entity: dict[str, Any]) -> str | None:
    instance_ids = _extract_entity_ids(entity.get("claims", {}), "P31")
    if "Q5" in instance_ids:
        return "Person"
    if any(instance_id in LOCATION_INSTANCE_IDS for instance_id in instance_ids):
        return "Location"
    if any(instance_id in ORGANIZATION_INSTANCE_IDS for instance_id in instance_ids):
        return "Company"
    return None


def _get_lang_value(block: dict[str, Any] | None, lang: str) -> str | None:
    if not block:
        return None
    entry = block.get(lang)
    if not entry:
        return None
    if isinstance(entry, dict):
        return entry.get("value")
    return None


def _get_aliases(block: dict[str, Any] | None, lang: str) -> list[str]:
    if not block:
        return []
    entries = block.get(lang, [])
    return [entry.get("value") for entry in entries if entry.get("value")]


def _extract_time(claims: dict[str, Any], prop: str) -> str | None:
    values = _extract_claim_values(claims, prop)
    if not values:
        return None
    time_value = values[0].get("time")
    if not time_value:
        return None
    try:
        parsed = datetime.fromisoformat(time_value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.date().isoformat()


def _extract_entity_label(claims: dict[str, Any], prop: str) -> str | None:
    ids = _extract_entity_ids(claims, prop)
    if not ids:
        return None
    session = _get_session()
    labels = _fetch_labels(ids, session)
    for entity_id in ids:
        label = labels.get(entity_id)
        if label:
            return label
    return None


def _extract_entity_ids(claims: dict[str, Any], prop: str) -> list[str]:
    ids: list[str] = []
    for value in _extract_claim_values(claims, prop):
        entity_id = value.get("id")
        if entity_id:
            ids.append(entity_id)
    return ids


def _extract_claim_values(claims: dict[str, Any], prop: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    claim_list = claims.get(prop) or []
    for claim in claim_list:
        datavalue = (claim.get("mainsnak") or {}).get("datavalue") or {}
        value = datavalue.get("value")
        if isinstance(value, dict):
            results.append(value)
    return results


def _fetch_labels(entity_ids: list[str], session: requests.Session) -> dict[str, str]:
    response = session.get(
        WIKIDATA_API,
        params={
            "action": "wbgetentities",
            "ids": "|".join(entity_ids),
            "props": "labels",
            "languages": "en",
            "format": "json",
        },
        timeout=20,
    )
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    entities = data.get("entities") or {}
    labels: dict[str, str] = {}
    for entity_id, entity in entities.items():
        label = _get_lang_value(entity.get("labels"), "en")
        if label:
            labels[entity_id] = label
    return labels


def _infer_label(entity: dict[str, Any]) -> str | None:
    label = _classify_entity(entity)
    if label in {"Person", "Company"}:
        return label
    instance_ids = _extract_entity_ids(entity.get("claims", {}), "P31")
    return "Company" if instance_ids else None
