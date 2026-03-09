import os
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError


def _normalize_neo4j_uri(uri: str | None) -> str | None:
    text = str(uri or "").strip()
    if not text:
        return None
    if ".bolt.neo4jsandbox.com:443" in text:
        return text.replace(".bolt.neo4jsandbox.com:443", ".neo4jsandbox.com:7687")
    return text


def _load_db_config():
    def _first(*keys: str, default: str | None = None) -> str | None:
        for key in keys:
            value = os.getenv(key)
            if value is not None and str(value).strip() != "":
                return value
        return default

    override_uri = _first("DELIBERATION_NEO4J_URI")
    override_user = _first("DELIBERATION_NEO4J_USER", "DELIBERATION_NEO4J_USERNAME")
    override_password = _first("DELIBERATION_NEO4J_PASSWORD")
    override_database = _first("DELIBERATION_NEO4J_DATABASE")
    if override_uri:
        return (
            _normalize_neo4j_uri(override_uri),
            override_user or _first("NEO4J_USER", "NEO4J_USERNAME", default="neo4j"),
            override_password
            or _first("NEO4J_PASSWORD", "NEO4J_PASS", default="change-this"),
            override_database or _first("NEO4J_DATABASE", default="neo4j"),
        )

    mode = os.getenv("DELIBERATION_DB_MODE", "local").lower()
    if mode == "sandbox":
        sandbox_uri = _first("NEO4J_SANDBOX_URI")
        sandbox_user = _first("NEO4J_SANDBOX_USER", "NEO4J_SANDBOX_USERNAME", default="neo4j")
        sandbox_password = _first("NEO4J_SANDBOX_PASSWORD")
        sandbox_database = _first("NEO4J_SANDBOX_DATABASE", default="neo4j")
        if sandbox_uri and sandbox_password:
            return (
                _normalize_neo4j_uri(sandbox_uri),
                sandbox_user,
                sandbox_password,
                sandbox_database,
            )

    primary_uri = _first("NEO4J_URI")
    primary_user = _first("NEO4J_USER", "NEO4J_USERNAME")
    primary_password = _first("NEO4J_PASSWORD", "NEO4J_PASS")
    primary_database = _first("NEO4J_DATABASE", default="neo4j")
    if primary_uri and primary_password:
        return (
            _normalize_neo4j_uri(primary_uri),
            primary_user or "neo4j",
            primary_password,
            primary_database,
        )

    # Safety fallback for deployments that only provide sandbox variables.
    sandbox_uri = _first("NEO4J_SANDBOX_URI")
    sandbox_password = _first("NEO4J_SANDBOX_PASSWORD")
    if sandbox_uri and sandbox_password:
        return (
            _normalize_neo4j_uri(sandbox_uri),
            _first("NEO4J_SANDBOX_USER", "NEO4J_SANDBOX_USERNAME", default="neo4j"),
            sandbox_password,
            _first("NEO4J_SANDBOX_DATABASE", default="neo4j"),
        )

    return (
        "bolt://localhost:7687",
        "neo4j",
        "change-this",
        "neo4j",
    )


NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE = _load_db_config()

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            connection_timeout=15,
        )
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


def db_health() -> dict:
    try:
        driver = get_driver()
        driver.verify_connectivity()
        with driver.session(database=NEO4J_DATABASE) as session:
            records = session.run("RETURN 1 AS ok").data()
        return {"ok": bool(records)}
    except Neo4jError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
