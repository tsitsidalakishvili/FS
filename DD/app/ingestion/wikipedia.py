from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

from app.ingestion.models import Entity, IngestionBatch, Relationship


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_REST = "https://en.wikipedia.org/api/rest_v1/page/summary"
WIKIPEDIA_SOURCE_ID = "source:wikipedia"


def fetch_wikipedia_profile(
    entity_name: str,
    *,
    target_label: str,
    target_id: str,
) -> IngestionBatch:
    query = str(entity_name or "").strip()
    if not query:
        return IngestionBatch(source="wikipedia", entities=[], relationships=[])

    title = _resolve_page_title(query)
    if not title:
        return IngestionBatch(source="wikipedia", entities=[], relationships=[])

    summary = _fetch_page_summary(title)
    if not summary:
        return IngestionBatch(source="wikipedia", entities=[], relationships=[])

    page_url = str(summary.get("content_urls", {}).get("desktop", {}).get("page") or "").strip()
    extract = str(summary.get("extract") or "").strip()
    image_url = str(summary.get("thumbnail", {}).get("source") or "").strip()
    normalized_title = str(summary.get("title") or title).strip()

    source_entity = Entity(
        label="Source",
        properties={
            "id": WIKIPEDIA_SOURCE_ID,
            "name": "Wikipedia",
            "type": "encyclopedia",
            "url": "https://www.wikipedia.org/",
        },
    )
    subject_props: dict[str, Any] = {
        "id": target_id,
        "wikipedia_title": normalized_title,
        "wikipedia_url": page_url,
        "source_refs": [ref for ref in [page_url] if ref],
    }
    if extract:
        subject_props["summary"] = extract
    if image_url:
        subject_props["image_url"] = image_url

    if target_label == "Person":
        subject_props.setdefault("full_name", query)
    else:
        subject_props.setdefault("name", query)

    subject_entity = Entity(label=target_label, properties=subject_props)
    relationship = Relationship(
        source_label=target_label,
        source_id=target_id,
        rel_type="LISTED_IN",
        target_label="Source",
        target_id=WIKIPEDIA_SOURCE_ID,
        properties={"classification": "public_profile", "source": "wikipedia"},
    )
    return IngestionBatch(
        source="wikipedia",
        entities=[source_entity, subject_entity],
        relationships=[relationship],
    )


def _resolve_page_title(entity_name: str) -> str:
    response = requests.get(
        WIKIPEDIA_API,
        params={
            "action": "query",
            "list": "search",
            "srsearch": entity_name,
            "utf8": 1,
            "format": "json",
            "srlimit": 1,
        },
        timeout=20,
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    results = (payload.get("query") or {}).get("search") or []
    if not results:
        return ""
    return str(results[0].get("title") or "").strip()


def _fetch_page_summary(title: str) -> dict[str, Any]:
    if not title:
        return {}
    response = requests.get(f"{WIKIPEDIA_REST}/{quote(title)}", timeout=20)
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    return payload
