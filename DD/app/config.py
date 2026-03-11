import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
DD_DIR = Path(__file__).resolve().parents[1]


def load_environment() -> None:
    # Match CRM's root-level .env loading, while allowing DD-specific overrides.
    load_dotenv(ROOT_DIR / ".env", override=False)
    load_dotenv(DD_DIR / ".env", override=True)


@dataclass(frozen=True)
class Settings:
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str
    news_api_key: str | None
    opensanctions_api_key: str | None
    opensanctions_dataset: str


def get_settings() -> Settings:
    load_environment()
    neo4j_user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME") or "neo4j"
    return Settings(
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=neo4j_user,
        neo4j_password=os.getenv("NEO4J_PASSWORD", "neo4j"),
        neo4j_database=os.getenv("NEO4J_DATABASE", "neo4j"),
        news_api_key=os.getenv("NEWS_API_KEY") or None,
        opensanctions_api_key=os.getenv("OPENSANCTIONS_API_KEY") or None,
        opensanctions_dataset=os.getenv("OPENSANCTIONS_DATASET", "default"),
    )
