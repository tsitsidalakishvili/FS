from __future__ import annotations

from typing import Any

from app.graph.neo4j import Neo4jClient


ALLOWED_ENTITY_LABELS = {"Person", "Company"}


def search_entities(client: Neo4jClient, term: str, limit: int = 25) -> list[dict[str, Any]]:
    query = """
    CALL {
        MATCH (p:Person)
        WHERE toLower(p.full_name) CONTAINS $term
           OR any(alias IN coalesce(p.aliases, []) WHERE toLower(alias) CONTAINS $term)
        RETURN p AS entity, "Person" AS label
        UNION
        MATCH (c:Company)
        WHERE toLower(c.name) CONTAINS $term
        RETURN c AS entity, "Company" AS label
    }
    RETURN entity, label
    LIMIT $limit
    """
    rows = client.run(query, {"term": term.lower(), "limit": limit})
    results = []
    for row in rows:
        entity = row["entity"]
        results.append(
            {
                "label": row["label"],
                "id": entity.get("id"),
                "name": entity.get("full_name") or entity.get("name") or entity.get("title"),
            }
        )
    return results


def get_entity(client: Neo4jClient, label: str, entity_id: str) -> dict[str, Any] | None:
    if label not in ALLOWED_ENTITY_LABELS:
        return None
    query = f"""
    MATCH (e:{label} {{id: $entity_id}})
    RETURN e AS entity
    LIMIT 1
    """
    rows = client.run(query, {"entity_id": entity_id})
    if not rows:
        return None
    return dict(rows[0]["entity"])


def get_neighbors(
    client: Neo4jClient, label: str, entity_id: str, limit: int = 200
) -> list[dict[str, Any]]:
    if label not in ALLOWED_ENTITY_LABELS:
        return []
    query = f"""
    MATCH (e:{label} {{id: $entity_id}})
    MATCH (e)-[r]-(n)
    RETURN e AS source, type(r) AS rel, properties(r) AS rel_props, n AS target
    LIMIT $limit
    """
    rows = client.run(query, {"entity_id": entity_id, "limit": limit})
    results = []
    for row in rows:
        target = row["target"]
        results.append(
            {
                "source_id": row["source"].get("id"),
                "rel": row["rel"],
                "rel_props": row["rel_props"],
                "target_id": target.get("id"),
                "target_label": next(iter(target.labels), None),
                "target_name": target.get("full_name") or target.get("name") or target.get("title"),
            }
        )
    return results


def get_risky_neighbors(
    client: Neo4jClient, label: str, entity_id: str, hops: int = 2, limit: int = 200
) -> list[dict[str, Any]]:
    if label not in ALLOWED_ENTITY_LABELS:
        return []
    query = f"""
    MATCH (e:{label} {{id: $entity_id}})
    MATCH (e)-[*1..{hops}]-(n)
    WHERE EXISTS {{
        MATCH (n)-[:LISTED_IN]->(:SanctionList)
    }} OR EXISTS {{
        MATCH (n)-[r:LISTED_IN]->(:Dataset)
        WHERE coalesce(r.classification, "") = "sanction"
           OR any(t IN coalesce(r.topics, []) WHERE toLower(t) CONTAINS "sanction")
    }} OR EXISTS {{
        MATCH (n)-[r:LISTED_IN]->(:Source)
        WHERE coalesce(r.classification, "") = "sanction"
           OR any(t IN coalesce(r.topics, []) WHERE toLower(t) CONTAINS "sanction")
    }}
    RETURN DISTINCT n AS node
    LIMIT $limit
    """
    rows = client.run(query, {"entity_id": entity_id, "limit": limit})
    results = []
    for row in rows:
        node = row["node"]
        results.append(
            {
                "id": node.get("id"),
                "label": next(iter(node.labels), None),
                "name": node.get("full_name") or node.get("name") or node.get("title"),
            }
        )
    return results
