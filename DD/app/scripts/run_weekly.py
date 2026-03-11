from app.config import get_settings
from app.graph.neo4j import Neo4jClient, Neo4jConfig
from app.monitoring.weekly import run_weekly_monitoring


def main() -> None:
    settings = get_settings()
    client = Neo4jClient(
        Neo4jConfig(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
    )
    try:
        run_weekly_monitoring(client, settings)
        print("Weekly monitoring completed.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
