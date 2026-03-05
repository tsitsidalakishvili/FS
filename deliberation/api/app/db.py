import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "change-this")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

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
