from __future__ import annotations

from app.config import Settings
from app.graph.neo4j import Neo4jClient
from app.graph.queries import list_tracked_entities
from app.ingestion.ingest import apply_batch
from app.ingestion.news import fetch_news_articles
from app.ingestion.models import IngestionBatch, Relationship


def run_weekly_monitoring(client: Neo4jClient, settings: Settings) -> None:
    entities = list_tracked_entities(client, limit=500)
    for entity in entities:
        entity_label = str(entity.get("label") or "").strip()
        entity_id = str(entity.get("id") or "").strip()
        name = entity.get("name")
        if not name or not entity_label or not entity_id:
            continue
        news_batch = fetch_news_articles(settings.news_api_key, query=name, max_results=5)
        if not news_batch.entities:
            continue

        relationships: list[Relationship] = []
        for article in news_batch.entities:
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
                    properties={"query": str(name).strip()},
                )
            )

        apply_batch(
            client,
            IngestionBatch(
                source="news_weekly",
                entities=news_batch.entities,
                relationships=relationships,
            ),
        )
