from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]


def load_environment() -> None:
    load_dotenv(ROOT_DIR / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str
    cors_origins: list[str]


def _parse_csv(value: str | None) -> list[str]:
    raw = str(value or "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_settings() -> Settings:
    load_environment()
    return Settings(
        app_name=os.getenv("CORE_API_NAME", "Freedom Square Core API"),
        app_env=os.getenv("CORE_API_ENV", "development"),
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME") or "neo4j",
        neo4j_password=os.getenv("NEO4J_PASSWORD", "neo4j"),
        neo4j_database=os.getenv("NEO4J_DATABASE", "neo4j"),
        cors_origins=_parse_csv(os.getenv("CORE_API_CORS_ORIGINS")),
    )
