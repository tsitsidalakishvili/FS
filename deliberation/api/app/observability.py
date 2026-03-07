import json
import logging
import os
import time
import uuid
from typing import Optional

import sentry_sdk
from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sentry_sdk.integrations.fastapi import FastApiIntegration


REQUEST_COUNT = Counter(
    "deliberation_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)
REQUEST_LATENCY_SECONDS = Histogram(
    "deliberation_http_request_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

logger = logging.getLogger("deliberation.api")


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, level, logging.INFO))


def setup_sentry(service_name: str = "fs-deliberation-api") -> bool:
    sentry_dsn = (os.getenv("DELIBERATION_SENTRY_DSN") or os.getenv("SENTRY_DSN") or "").strip()
    if not sentry_dsn:
        return False
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        release=os.getenv("APP_RELEASE"),
        traces_sample_rate=_float_env("SENTRY_TRACES_SAMPLE_RATE", 0.0),
        profiles_sample_rate=_float_env("SENTRY_PROFILES_SAMPLE_RATE", 0.0),
        send_default_pii=_bool_env("SENTRY_SEND_DEFAULT_PII", False),
        integrations=[FastApiIntegration()],
        server_name=service_name,
    )
    return True


def install_api_observability(app: FastAPI) -> None:
    _setup_logging()
    setup_sentry()

    @app.middleware("http")
    async def request_observability_middleware(request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        status_code = 500
        route_path = request.url.path
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["x-request-id"] = request_id
            return response
        finally:
            elapsed = time.perf_counter() - start
            route = request.scope.get("route")
            if route is not None and getattr(route, "path", None):
                route_path = route.path
            REQUEST_COUNT.labels(request.method, route_path, str(status_code)).inc()
            REQUEST_LATENCY_SECONDS.labels(request.method, route_path).observe(elapsed)
            log_event = {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": route_path,
                "status_code": status_code,
                "duration_ms": round(elapsed * 1000.0, 2),
                "client_ip": request.client.host if request.client else None,
            }
            logger.info(json.dumps(log_event, separators=(",", ":")))

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def readiness_payload(
    *,
    db_ok: bool,
    db_message: str,
    redis_configured: bool,
    redis_ok: Optional[bool],
) -> dict:
    status = "ok" if db_ok and (not redis_configured or bool(redis_ok)) else "degraded"
    return {
        "status": status,
        "checks": {
            "neo4j": {"ok": db_ok, "message": db_message},
            "redis": {
                "configured": redis_configured,
                "ok": redis_ok if redis_configured else None,
                "message": "ok" if redis_ok else ("not configured" if not redis_configured else "unreachable"),
            },
        },
    }
