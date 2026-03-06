import os
from neo4j import GraphDatabase


def _load_db_config():
    override_uri = os.getenv("DELIBERATION_NEO4J_URI")
    override_user = os.getenv("DELIBERATION_NEO4J_USER")
    override_password = os.getenv("DELIBERATION_NEO4J_PASSWORD")
    override_database = os.getenv("DELIBERATION_NEO4J_DATABASE")
    if override_uri:
        return (
            override_uri,
            override_user or os.getenv("NEO4J_USER", "neo4j"),
            override_password or os.getenv("NEO4J_PASSWORD", "change-this"),
            override_database or os.getenv("NEO4J_DATABASE", "neo4j"),
        )

    mode = os.getenv("DELIBERATION_DB_MODE", "local").lower()
    if mode == "sandbox":
        sandbox_uri = os.getenv("NEO4J_SANDBOX_URI")
        sandbox_user = (
            os.getenv("NEO4J_SANDBOX_USER")
            or os.getenv("NEO4J_SANDBOX_USERNAME")
            or "neo4j"
        )
        sandbox_password = os.getenv("NEO4J_SANDBOX_PASSWORD")
        sandbox_database = os.getenv("NEO4J_SANDBOX_DATABASE", "neo4j")
        if sandbox_uri and sandbox_password:
            return sandbox_uri, sandbox_user, sandbox_password, sandbox_database

    return (
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        os.getenv("NEO4J_USER", "neo4j"),
        os.getenv("NEO4J_PASSWORD", "change-this"),
        os.getenv("NEO4J_DATABASE", "neo4j"),
    )


NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE = _load_db_config()

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def close_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def _execute_write(session, query):
    if hasattr(session, "execute_write"):
        session.execute_write(lambda tx: tx.run(query))
    else:
        session.write_transaction(lambda tx: tx.run(query))


def init_constraints():
    driver = get_driver()
    queries = [
        "CREATE CONSTRAINT conversation_id IF NOT EXISTS FOR (c:Conversation) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT comment_id IF NOT EXISTS FOR (c:Comment) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT participant_id IF NOT EXISTS FOR (p:Participant) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT cluster_id IF NOT EXISTS FOR (c:Cluster) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT analysis_run_id IF NOT EXISTS FOR (a:AnalysisRun) REQUIRE a.id IS UNIQUE",
    ]
    with driver.session(database=NEO4J_DATABASE) as session:
        for query in queries:
            _execute_write(session, query)
