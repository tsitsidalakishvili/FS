from __future__ import annotations

import os
from typing import Any

from neo4j import Driver, GraphDatabase
from neo4j.exceptions import ServiceUnavailable

from .config import get_settings


settings = get_settings()
_driver: Driver | None = None
_active_target: dict[str, str] | None = None


def _normalize_neo4j_uri(uri: str | None) -> str | None:
    text = str(uri or "").strip()
    if not text:
        return None
    if ".bolt.neo4jsandbox.com" in text:
        text = text.replace(".bolt.neo4jsandbox.com:443", ".neo4jsandbox.com:7687")
        text = text.replace(".bolt.neo4jsandbox.com", ".neo4jsandbox.com:7687")
    return text


def _first(*keys: str, default: str | None = None) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value is not None and str(value).strip() != "":
            return value
    return default


def _build_db_candidates() -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()

    def add_candidate(source: str, uri: str | None, user: str | None, password: str | None, database: str | None) -> None:
        normalized_uri = _normalize_neo4j_uri(uri)
        text_password = str(password or "").strip()
        text_user = str(user or "neo4j").strip() or "neo4j"
        text_db = str(database or "neo4j").strip() or "neo4j"
        if not normalized_uri or not text_password:
            return
        key = (normalized_uri, text_user, text_password, text_db)
        if key in seen:
            return
        seen.add(key)
        candidates.append(
            {
                "source": source,
                "uri": normalized_uri,
                "user": text_user,
                "password": text_password,
                "database": text_db,
            }
        )

    add_candidate(
        "NEO4J_*",
        settings.neo4j_uri,
        settings.neo4j_user,
        settings.neo4j_password,
        settings.neo4j_database,
    )
    add_candidate(
        "DELIBERATION_NEO4J_*",
        _first("DELIBERATION_NEO4J_URI"),
        _first("DELIBERATION_NEO4J_USER", "DELIBERATION_NEO4J_USERNAME"),
        _first("DELIBERATION_NEO4J_PASSWORD"),
        _first("DELIBERATION_NEO4J_DATABASE", default="neo4j"),
    )
    add_candidate(
        "NEO4J_SANDBOX_*",
        _first("NEO4J_SANDBOX_URI"),
        _first("NEO4J_SANDBOX_USER", "NEO4J_SANDBOX_USERNAME", default="neo4j"),
        _first("NEO4J_SANDBOX_PASSWORD"),
        _first("NEO4J_SANDBOX_DATABASE", default="neo4j"),
    )
    return candidates


def get_driver() -> Driver:
    global _driver, _active_target
    if _driver is not None:
        return _driver

    errors: list[str] = []
    for target in _build_db_candidates():
        candidate_driver: Driver | None = None
        try:
            candidate_driver = GraphDatabase.driver(
                target["uri"],
                auth=(target["user"], target["password"]),
                connection_timeout=12,
                connection_acquisition_timeout=12,
            )
            candidate_driver.verify_connectivity()
            with candidate_driver.session(database=target["database"]) as session:
                session.run("RETURN 1 AS ok").consume()
            _driver = candidate_driver
            _active_target = target
            return _driver
        except Exception as exc:
            errors.append(
                f"{target['source']}[{target['uri']}|{target['database']}] => {exc}"
            )
            try:
                if candidate_driver is not None:
                    candidate_driver.close()
            except Exception:
                pass
    raise RuntimeError("No working Neo4j configuration. " + " ; ".join(errors))


class Neo4jClient:
    def run(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        driver = get_driver()
        target_database = str((_active_target or {}).get("database") or settings.neo4j_database)
        try:
            with driver.session(database=target_database) as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except ServiceUnavailable:
            with driver.session(database=target_database) as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]

    def health(self) -> dict[str, Any]:
        try:
            rows = self.run("RETURN 1 AS ok")
            active = _active_target or {}
            return {
                "ok": bool(rows),
                "database": active.get("database") or settings.neo4j_database,
                "uri": active.get("uri") or settings.neo4j_uri,
                "source": active.get("source") or "unknown",
            }
        except Exception as exc:
            return {
                "ok": False,
                "database": settings.neo4j_database,
                "uri": settings.neo4j_uri,
                "error": str(exc),
            }


client = Neo4jClient()


def get_client() -> Neo4jClient:
    return client


def close_client() -> None:
    global _driver, _active_target
    if _driver is not None:
        _driver.close()
        _driver = None
    _active_target = None
