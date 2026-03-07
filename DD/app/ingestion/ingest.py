from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Iterable

from app.graph.neo4j import Neo4jClient
from app.ingestion.models import Entity, IngestionBatch, Relationship


ALLOWED_LABELS = {
    "Person",
    "Company",
    "NewsArticle",
    "Location",
    "SanctionList",
    "Source",
    "Dataset",
}

REL_TYPE_RE = re.compile(r"^[A-Z_]+$")


def apply_batch(client: Neo4jClient, batch: IngestionBatch) -> None:
    source = _normalize_source(batch.source)
    ingested_at = _utc_now_iso()
    for entity in batch.entities:
        merge_entity(client, entity, source, ingested_at)

    for rel in batch.relationships:
        merge_relationship(client, rel, source, ingested_at)


def merge_entities(client: Neo4jClient, entities: Iterable[Entity], source: str) -> None:
    source = _normalize_source(source)
    ingested_at = _utc_now_iso()
    for entity in entities:
        merge_entity(client, entity, source, ingested_at)


def merge_entity(
    client: Neo4jClient, entity: Entity, source: str, ingested_at: str | None = None
) -> None:
    if entity.label not in ALLOWED_LABELS:
        return
    source = _normalize_source(source)
    ingested_at = ingested_at or _utc_now_iso()
    merge_key = "id"
    entity_id = entity.properties.get("id")
    if entity.label == "SanctionList":
        merge_key = "name"
        entity_id = entity.properties.get("name") or entity_id
    if not entity_id:
        return
    props = dict(entity.properties)
    source_refs: list[str] = []
    if source:
        source_refs.append(source)
    props_source_refs = props.pop("source_refs", None)
    if isinstance(props_source_refs, list):
        source_refs.extend([ref for ref in props_source_refs if ref])

    query = f"""
    MERGE (e:{entity.label} {{{merge_key}: $entity_id}})
    SET e += $props
    SET e.ingestion_source = coalesce(e.ingestion_source, $source)
    SET e.ingested_at = coalesce(e.ingested_at, $ingested_at)
    SET e.last_ingestion_source = $source
    SET e.last_ingested_at = $ingested_at
    WITH e
    FOREACH (ref IN $source_refs |
        SET e.source_refs = CASE
            WHEN e.source_refs IS NULL THEN [ref]
            WHEN ref IN e.source_refs THEN e.source_refs
            ELSE e.source_refs + ref
        END
    )
    """
    client.run_write(
        query,
        {
            "entity_id": entity_id,
            "props": props,
            "source": source,
            "ingested_at": ingested_at,
            "source_refs": source_refs,
        },
    )


def merge_relationships(
    client: Neo4jClient, relationships: Iterable[Relationship], source: str
) -> None:
    source = _normalize_source(source)
    ingested_at = _utc_now_iso()
    for rel in relationships:
        merge_relationship(client, rel, source, ingested_at)


def merge_relationship(
    client: Neo4jClient, rel: Relationship, source: str, ingested_at: str | None = None
) -> None:
    if rel.source_label not in ALLOWED_LABELS or rel.target_label not in ALLOWED_LABELS:
        return
    if not REL_TYPE_RE.match(rel.rel_type):
        return
    if not rel.source_id or not rel.target_id:
        return

    source = _normalize_source(source)
    ingested_at = ingested_at or _utc_now_iso()
    props = dict(rel.properties)
    if source:
        props.setdefault("source", source)
    props.setdefault("ingestion_source", source)
    props.setdefault("ingested_at", ingested_at)

    query = f"""
    MATCH (s:{rel.source_label} {{id: $source_id}})
    MATCH (t:{rel.target_label} {{id: $target_id}})
    MERGE (s)-[r:{rel.rel_type}]->(t)
    SET r += $props
    SET r.ingestion_source = coalesce(r.ingestion_source, $source)
    SET r.ingested_at = coalesce(r.ingested_at, $ingested_at)
    SET r.last_ingestion_source = $source
    SET r.last_ingested_at = $ingested_at
    """
    client.run_write(
        query,
        {
            "source_id": rel.source_id,
            "target_id": rel.target_id,
            "props": props,
            "source": source,
            "ingested_at": ingested_at,
        },
    )


def _normalize_source(source: str | None) -> str:
    text = str(source or "").strip()
    return text or "unknown"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
