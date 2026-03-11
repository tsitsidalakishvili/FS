from __future__ import annotations

import re
from typing import Any

from app.graph.neo4j import Neo4jClient


ALLOWED_ENTITY_LABELS = {"Person", "Company"}
LUCENE_SPECIAL_CHARS_RE = re.compile(r'[+\-!(){}\[\]^"~*?:\\/]|&&|\|\|')


def search_entities(client: Neo4jClient, term: str, limit: int = 25) -> list[dict[str, Any]]:
    clean_term = (term or "").strip()
    if not clean_term:
        return []

    fulltext_query = _build_fulltext_query(clean_term)
    if fulltext_query:
        try:
            rows = client.run(
                """
                CALL {
                    CALL db.index.fulltext.queryNodes("dd_person_search", $query) YIELD node, score
                    RETURN node AS entity, "Person" AS label, score
                    UNION ALL
                    CALL db.index.fulltext.queryNodes("dd_company_search", $query) YIELD node, score
                    RETURN node AS entity, "Company" AS label, score
                }
                RETURN entity, label, score
                ORDER BY score DESC
                LIMIT $limit
                """,
                {"query": fulltext_query, "limit": limit},
            )
            return _map_entity_rows(rows)
        except Exception:
            # Fallback keeps search usable until schema/indexes are initialized.
            pass

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
    rows = client.run(query, {"term": clean_term.lower(), "limit": limit})
    return _map_entity_rows(rows)


def list_tracked_entities(client: Neo4jClient, limit: int = 100) -> list[dict[str, Any]]:
    rows = client.run(
        """
        CALL {
            MATCH (p:Person)
            RETURN "Person" AS label, p.id AS id, coalesce(p.full_name, p.name) AS name, coalesce(p.aliases, []) AS aliases
            UNION ALL
            MATCH (c:Company)
            RETURN "Company" AS label, c.id AS id, coalesce(c.name, c.full_name) AS name, coalesce(c.aliases, []) AS aliases
        }
        WITH label, id, name, aliases
        WHERE id IS NOT NULL AND name IS NOT NULL AND trim(name) <> ""
        RETURN label, id, name, aliases
        ORDER BY toLower(name) ASC
        LIMIT $limit
        """,
        {"limit": limit},
    )
    return [
        {
            "label": row["label"],
            "id": row["id"],
            "name": row["name"],
            "aliases": row.get("aliases") or [],
        }
        for row in rows
    ]


def get_latest_monitoring_run(client: Neo4jClient) -> dict[str, Any] | None:
    rows = client.run(
        """
        MATCH (run:MonitoringRun)
        RETURN run
        ORDER BY coalesce(run.started_at, run.completed_at) DESC
        LIMIT 1
        """
    )
    if not rows:
        return None
    return dict(rows[0]["run"])


def list_investigation_runs(
    client: Neo4jClient, subject_id: str, limit: int = 10
) -> list[dict[str, Any]]:
    clean_subject_id = str(subject_id or "").strip()
    if not clean_subject_id:
        return []
    rows = client.run(
        """
        MATCH (s {id: $subject_id})-[:HAS_INVESTIGATION]->(run:InvestigationRun)
        RETURN run
        ORDER BY coalesce(run.started_at, run.completed_at, run.created_at) DESC
        LIMIT $limit
        """,
        {"subject_id": clean_subject_id, "limit": limit},
    )
    return [dict(row["run"]) for row in rows]


def _build_fulltext_query(term: str) -> str:
    cleaned = LUCENE_SPECIAL_CHARS_RE.sub(" ", term)
    tokens = [token.strip().lower() for token in cleaned.split() if token.strip()]
    if not tokens:
        return ""
    return " AND ".join(f"{token}*" for token in tokens)


def _map_entity_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
