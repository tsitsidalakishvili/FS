from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.config import Settings
from app.graph.neo4j import Neo4jClient
from app.graph.queries import list_tracked_entities
from app.ingestion.gdelt import fetch_gdelt_articles
from app.ingestion.ingest import apply_batch
from app.ingestion.models import IngestionBatch, Relationship
from app.ingestion.news import fetch_news_articles


def run_weekly_monitoring(client: Neo4jClient, settings: Settings) -> dict[str, object]:
    run_id = f"monitoring-run-{uuid4()}"
    started_at = _utc_now_iso()
    monitoring_sources = ["gdelt"]
    if settings.news_api_key:
        monitoring_sources.insert(0, "newsapi")

    summary: dict[str, object] = {
        "id": run_id,
        "status": "running",
        "started_at": started_at,
        "completed_at": "",
        "tracked_entities": 0,
        "processed_entities": 0,
        "query_count": 0,
        "article_count": 0,
        "newsapi_articles": 0,
        "gdelt_articles": 0,
        "failure_count": 0,
        "monitoring_sources": monitoring_sources,
        "error_messages": [],
    }
    _persist_monitoring_run(client, summary)

    entities = list_tracked_entities(client, limit=500)
    summary["tracked_entities"] = len(entities)

    for entity in entities:
        entity_label = str(entity.get("label") or "").strip()
        entity_id = str(entity.get("id") or "").strip()
        name = str(entity.get("name") or "").strip()
        if not name or not entity_label or not entity_id:
            continue

        search_queries = _build_search_queries(name, entity.get("aliases") or [])
        if not search_queries:
            continue

        entity_articles = 0
        for query in search_queries:
            summary["query_count"] = int(summary["query_count"]) + 1

            if settings.news_api_key:
                try:
                    news_batch = fetch_news_articles(
                        settings.news_api_key, query=query, max_results=5
                    )
                    news_batch = _attach_mentions(
                        news_batch,
                        entity_label=entity_label,
                        entity_id=entity_id,
                        query=query,
                        relation_source="newsapi",
                    )
                    if news_batch.entities:
                        apply_batch(client, news_batch)
                    news_count = _count_article_entities(news_batch)
                    summary["newsapi_articles"] = int(summary["newsapi_articles"]) + news_count
                    summary["article_count"] = int(summary["article_count"]) + news_count
                    entity_articles += news_count
                except Exception as exc:
                    _append_monitoring_error(
                        summary, f"newsapi::{entity_id}::{query}::{exc}"
                    )

            try:
                gdelt_batch = fetch_gdelt_articles(query=query, max_results=5)
                gdelt_batch = _attach_mentions(
                    gdelt_batch,
                    entity_label=entity_label,
                    entity_id=entity_id,
                    query=query,
                    relation_source="gdelt",
                )
                if gdelt_batch.entities:
                    apply_batch(client, gdelt_batch)
                gdelt_count = _count_article_entities(gdelt_batch)
                summary["gdelt_articles"] = int(summary["gdelt_articles"]) + gdelt_count
                summary["article_count"] = int(summary["article_count"]) + gdelt_count
                entity_articles += gdelt_count
            except Exception as exc:
                _append_monitoring_error(summary, f"gdelt::{entity_id}::{query}::{exc}")

        if entity_articles > 0:
            summary["processed_entities"] = int(summary["processed_entities"]) + 1

    summary["completed_at"] = _utc_now_iso()
    summary["status"] = (
        "completed_with_errors"
        if int(summary["failure_count"]) > 0
        else "completed"
    )
    _persist_monitoring_run(client, summary)
    return summary


def _build_search_queries(name: str, aliases: list[object]) -> list[str]:
    values = [str(name or "").strip()]
    for alias in aliases:
        text = str(alias or "").strip()
        if text:
            values.append(text)
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if not value or key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique[:4]


def _attach_mentions(
    article_batch: IngestionBatch,
    *,
    entity_label: str,
    entity_id: str,
    query: str,
    relation_source: str,
) -> IngestionBatch:
    relationships = list(article_batch.relationships)
    for article in article_batch.entities:
        if article.label != "NewsArticle":
            continue
        article_id = str(article.properties.get("id") or "").strip()
        if not article_id:
            continue
        relationships.append(
            Relationship(
                source_label=entity_label,
                source_id=entity_id,
                rel_type="MENTIONED_IN",
                target_label="NewsArticle",
                target_id=article_id,
                properties={"query": query, "source": relation_source},
            )
        )
    return IngestionBatch(
        source=article_batch.source,
        entities=article_batch.entities,
        relationships=relationships,
    )


def _count_article_entities(batch: IngestionBatch) -> int:
    return sum(1 for entity in batch.entities if entity.label == "NewsArticle")


def _append_monitoring_error(summary: dict[str, object], message: str) -> None:
    errors = list(summary.get("error_messages") or [])
    errors.append(str(message))
    summary["error_messages"] = errors[:25]
    summary["failure_count"] = int(summary.get("failure_count") or 0) + 1


def _persist_monitoring_run(client: Neo4jClient, summary: dict[str, object]) -> None:
    client.run_write(
        """
        MERGE (run:MonitoringRun {id: $id})
        SET run += $props
        """,
        {
            "id": summary["id"],
            "props": {
                "status": summary["status"],
                "started_at": summary["started_at"],
                "completed_at": summary["completed_at"] or None,
                "tracked_entities": int(summary["tracked_entities"]),
                "processed_entities": int(summary["processed_entities"]),
                "query_count": int(summary["query_count"]),
                "article_count": int(summary["article_count"]),
                "newsapi_articles": int(summary["newsapi_articles"]),
                "gdelt_articles": int(summary["gdelt_articles"]),
                "failure_count": int(summary["failure_count"]),
                "monitoring_sources": list(summary.get("monitoring_sources") or []),
                "error_messages": list(summary.get("error_messages") or []),
            },
        },
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
