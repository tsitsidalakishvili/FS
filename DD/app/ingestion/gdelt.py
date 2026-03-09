from __future__ import annotations

from datetime import datetime
from typing import Any

import requests

from app.ingestion.models import Entity, IngestionBatch


GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


def fetch_gdelt_articles(query: str, max_results: int = 15) -> IngestionBatch:
    search_term = str(query or "").strip()
    if not search_term:
        return IngestionBatch(source="gdelt", entities=[], relationships=[])

    response = requests.get(
        GDELT_DOC_API,
        params={
            "query": search_term,
            "mode": "artlist",
            "format": "json",
            "sort": "DateDesc",
            "maxrecords": int(max_results),
        },
        timeout=25,
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()

    entities: list[Entity] = []
    for article in payload.get("articles", []) or []:
        url = str(article.get("url") or "").strip()
        if not url:
            continue
        seen_date = str(article.get("seendate") or "").strip()
        published_date = _parse_seen_date(seen_date)
        title = str(article.get("title") or "").strip()
        source_name = str(article.get("sourceCommonName") or article.get("domain") or "").strip()
        entities.append(
            Entity(
                label="NewsArticle",
                properties={
                    "id": url,
                    "title": title or url,
                    "source": source_name or "GDELT",
                    "published_date": published_date,
                    "url": url,
                    "summary": str(article.get("socialimage") or article.get("language") or "").strip()
                    or None,
                    "source_refs": [url],
                },
            )
        )

    return IngestionBatch(source="gdelt", entities=entities, relationships=[])


def _parse_seen_date(value: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.strptime(text, "%Y%m%d%H%M%S")
    except ValueError:
        return None
    return parsed.date().isoformat()
