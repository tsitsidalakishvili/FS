from app.graph.neo4j import Neo4jClient


CONSTRAINTS = [
    "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (n:Person) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (n:Company) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT news_id IF NOT EXISTS FOR (n:NewsArticle) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT location_id IF NOT EXISTS FOR (n:Location) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT sanction_id IF NOT EXISTS FOR (n:SanctionList) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT source_id IF NOT EXISTS FOR (n:Source) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT dataset_id IF NOT EXISTS FOR (n:Dataset) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT monitoring_run_id IF NOT EXISTS FOR (n:MonitoringRun) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT investigation_run_id IF NOT EXISTS FOR (n:InvestigationRun) REQUIRE n.id IS UNIQUE",
]

INDEXES = [
    "CREATE FULLTEXT INDEX dd_person_search IF NOT EXISTS FOR (n:Person) ON EACH [n.full_name, n.aliases]",
    "CREATE FULLTEXT INDEX dd_company_search IF NOT EXISTS FOR (n:Company) ON EACH [n.name, n.aliases]",
]


def initialize_schema(client: Neo4jClient) -> None:
    for statement in CONSTRAINTS:
        client.run_write(statement)
    for statement in INDEXES:
        client.run_write(statement)
