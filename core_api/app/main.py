from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from .config import get_settings
from .db import close_client, get_client
from .routes.crm import router as crm_router
from .routes.due_diligence import router as dd_router


settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(crm_router)
app.include_router(dd_router)


@app.get("/")
def root():
    return {
        "service": settings.app_name,
        "environment": settings.app_env,
        "health": "/healthz",
        "modules": {
            "crm": "/api/v1/crm",
            "due_diligence": "/api/v1/due-diligence",
        },
    }


@app.get("/healthz")
def healthz():
    health = get_client().health()
    return {
        "status": "ok" if health.get("ok") else "degraded",
        "service": settings.app_name,
        "environment": settings.app_env,
        "neo4j": health,
    }


@app.on_event("shutdown")
def on_shutdown() -> None:
    close_client()


@app.exception_handler(ServiceUnavailable)
def handle_service_unavailable(_: Request, exc: ServiceUnavailable):
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Neo4j is unavailable for the Core API.",
            "error": str(exc),
        },
    )


@app.exception_handler(Neo4jError)
def handle_neo4j_error(_: Request, exc: Neo4jError):
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Neo4j query failed for the Core API.",
            "error": str(exc),
        },
    )


@app.exception_handler(RuntimeError)
def handle_runtime_error(_: Request, exc: RuntimeError):
    message = str(exc)
    if "No working Neo4j configuration" in message:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Neo4j configuration is invalid or unreachable for the Core API.",
                "error": message,
            },
        )
    return JSONResponse(status_code=500, content={"detail": message})
