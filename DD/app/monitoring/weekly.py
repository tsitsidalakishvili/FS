from __future__ import annotations

from app.config import Settings
from app.graph.neo4j import Neo4jClient
from app.graph.queries import search_entities
from app.ingestion.ingest import apply_batch
from app.ingestion.news import fetch_news_articles


def run_weekly_monitoring(client: Neo4jClient, settings: Settings) -> None:
    # Placeholder: loop through tracked entities and pull recent news.
    entities = search_entities(client, term="", limit=100)
    for entity in entities:
        name = entity.get("name")
        if not name:
            continue
        batch = fetch_news_articles(settings.news_api_key, query=name, max_results=5)
        apply_batch(client, batch)
