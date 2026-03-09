from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_dossier_snapshot(
    *,
    subject: dict[str, str],
    entity: dict[str, Any],
    neighbors: list[dict[str, Any]],
    risky: list[dict[str, Any]],
    source_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    profile = {
        "name": subject["name"],
        "label": subject["label"],
        "id": subject["id"],
        "summary": entity.get("summary"),
        "aliases": entity.get("aliases") or [],
        "birth_date": entity.get("birth_date"),
        "nationality": entity.get("nationality"),
        "jurisdiction": entity.get("jurisdiction"),
        "source_refs": entity.get("source_refs") or [],
    }
    relations = []
    for row in neighbors:
        relations.append(
            {
                "relationship": row.get("rel"),
                "target_name": row.get("target_name"),
                "target_label": row.get("target_label"),
            }
        )
    top_relations = relations[:20]
    risk_hits = [
        {
            "name": row.get("name"),
            "label": row.get("label"),
            "id": row.get("id"),
        }
        for row in risky[:20]
    ]
    media_hits = [
        {
            "title": row.get("target_name"),
            "source": (row.get("rel_props") or {}).get("source"),
            "published_date": (row.get("rel_props") or {}).get("published_date"),
            "url": row.get("target_id"),
        }
        for row in neighbors
        if row.get("target_label") == "NewsArticle"
    ][:25]

    return {
        "generated_at": generated_at,
        "subject": subject,
        "profile": profile,
        "source_runs": source_runs,
        "risk_hits": risk_hits,
        "key_connections": top_relations,
        "media_hits": media_hits,
    }


def dossier_markdown(snapshot: dict[str, Any]) -> str:
    subject = snapshot.get("subject") or {}
    profile = snapshot.get("profile") or {}
    source_runs = snapshot.get("source_runs") or []
    risk_hits = snapshot.get("risk_hits") or []
    connections = snapshot.get("key_connections") or []
    media_hits = snapshot.get("media_hits") or []

    lines: list[str] = []
    lines.append(f"# Dossier: {subject.get('name', 'Unknown')}")
    lines.append("")
    lines.append(f"- Generated at: {snapshot.get('generated_at', '')}")
    lines.append(f"- Type: {subject.get('label', '')}")
    lines.append(f"- ID: {subject.get('id', '')}")
    if profile.get("birth_date"):
        lines.append(f"- Birth date: {profile.get('birth_date')}")
    if profile.get("nationality"):
        lines.append(f"- Nationality: {profile.get('nationality')}")
    if profile.get("jurisdiction"):
        lines.append(f"- Jurisdiction: {profile.get('jurisdiction')}")
    lines.append("")

    lines.append("## Profile summary")
    lines.append(str(profile.get("summary") or "No profile summary available."))
    lines.append("")

    lines.append("## Source coverage")
    if source_runs:
        for row in source_runs:
            status = "OK" if row.get("ok") else "Skipped/Failed"
            detail = str(row.get("detail") or "").strip()
            count = int(row.get("items") or 0)
            suffix = f" ({detail})" if detail else ""
            lines.append(f"- {row.get('source')}: {status}, items={count}{suffix}")
    else:
        lines.append("- No sources were run.")
    lines.append("")

    lines.append("## Risk indicators (2-hop)")
    if risk_hits:
        for row in risk_hits:
            lines.append(f"- {row.get('name')} ({row.get('label')})")
    else:
        lines.append("- No risky neighbors detected.")
    lines.append("")

    lines.append("## Key connections")
    if connections:
        for row in connections:
            lines.append(
                f"- {row.get('relationship')} -> {row.get('target_name')} ({row.get('target_label')})"
            )
    else:
        lines.append("- No connections captured.")
    lines.append("")

    lines.append("## Recent media mentions")
    if media_hits:
        for row in media_hits:
            title = row.get("title") or row.get("url")
            source = row.get("source") or "unknown"
            date = row.get("published_date") or ""
            lines.append(f"- {title} [{source}] {date}".strip())
    else:
        lines.append("- No media mentions captured.")
    lines.append("")
    return "\n".join(lines)
