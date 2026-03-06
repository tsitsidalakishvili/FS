from __future__ import annotations

from datetime import datetime
from typing import Any

import requests

from app.ingestion.models import Entity, IngestionBatch, Relationship


def fetch_news_articles(
    api_key: str | None, query: str, max_results: int = 10
) -> IngestionBatch:
    if not api_key:
        return IngestionBatch(source="news", entities=[], relationships=[])

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "pageSize": max_results,
        "language": "en",
        "sortBy": "publishedAt",
        "apiKey": api_key,
    }
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data: dict[str, Any] = response.json()

    entities: list[Entity] = []
    relationships: list[Relationship] = []
    for article in data.get("articles", []):
        article_id = article.get("url")
        if not article_id:
            continue
        published = article.get("publishedAt")
        published_date = None
        if published:
            published_date = datetime.fromisoformat(published.replace("Z", "+00:00")).date().isoformat()

        entities.append(
            Entity(
                label="NewsArticle",
                properties={
                    "id": article_id,
                    "title": article.get("title"),
                    "source": (article.get("source") or {}).get("name"),
                    "published_date": published_date,
                    "url": article.get("url"),
                    "summary": article.get("description"),
                },
            )
        )

    return IngestionBatch(source="news", entities=entities, relationships=relationships)
