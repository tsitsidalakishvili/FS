import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Response

load_dotenv(
    dotenv_path=os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
    ),
    override=True,
)

from .cache import close_redis_client, ping_redis
from .db import NEO4J_DATABASE, close_driver, get_driver, init_constraints
from .observability import install_api_observability, readiness_payload
from .routes import router

def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _neo4j_ready():
    if _bool_env("DELIBERATION_SKIP_DB_INIT", False):
        return True, "skipped"
    try:
        driver = get_driver()
        with driver.session(database=NEO4J_DATABASE) as session:
            session.run("RETURN 1 AS ok").single()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not _bool_env("DELIBERATION_SKIP_DB_INIT", False):
        init_constraints()
    try:
        yield
    finally:
        close_driver()
        close_redis_client()


app = FastAPI(title="Polis-style Deliberation API", lifespan=lifespan)
install_api_observability(app)
app.include_router(router)


@app.get("/")
def root():
    return {
        "service": "fs-deliberation-api",
        "status": "ok",
        "docs": "/docs",
        "health": "/healthz",
        "ready": "/readyz",
        "metrics": "/metrics",
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz(response: Response):
    db_ok, db_message = _neo4j_ready()
    redis_configured = bool((os.getenv("REDIS_URL") or "").strip())
    redis_ok = ping_redis() if redis_configured else None
    payload = readiness_payload(
        db_ok=db_ok,
        db_message=db_message,
        redis_configured=redis_configured,
        redis_ok=redis_ok,
    )
    if payload["status"] != "ok":
        response.status_code = 503
    return payload
