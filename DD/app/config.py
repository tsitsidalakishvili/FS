import os
from dataclasses import dataclass


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
