from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware import Middleware

from .api.routes.health import router as health_router
from .api.routes.jobs import router as jobs_router
from .config import Settings
from .db import Base, build_engine, build_session_factory
from .errors import (
    AppError,
    handle_app_error,
    handle_http_exception,
    handle_unexpected_error,
    handle_validation_error,
)
from .tracing import RequestTracingMiddleware
from .worker.queue import RedisTaskQueue
from .worker.tasks import DefaultJobProcessor


def create_app(settings: Settings | None = None, task_queue=None) -> FastAPI:
    app_settings = settings or Settings.from_env()
    middleware = [Middleware(RequestTracingMiddleware, request_id_header=app_settings.request_id_header)]
    app = FastAPI(
        title="Secure Deliberation Backend API",
        version="1.0.0",
        description="Contract-first backend APIs with SQLAlchemy persistence and Redis worker integration.",
        middleware=middleware,
    )

    engine = build_engine(app_settings.database_url)
    session_factory = build_session_factory(engine)
    queue = task_queue or RedisTaskQueue.from_url(app_settings.redis_url, app_settings.queue_name)

    app.state.settings = app_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.task_queue = queue
    app.state.job_processor = DefaultJobProcessor()

    @app.on_event("startup")
    def on_startup():
        Base.metadata.create_all(bind=engine)

    @app.on_event("shutdown")
    def on_shutdown():
        engine.dispose()

    @app.exception_handler(AppError)
    async def _app_error_handler(request, exc: AppError):
        return await handle_app_error(request, exc)

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(request, exc: RequestValidationError):
        return await handle_validation_error(request, exc)

    from fastapi import HTTPException

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(request, exc: HTTPException):
        return await handle_http_exception(request, exc)

    @app.exception_handler(Exception)
    async def _unexpected_handler(request, exc: Exception):
        return await handle_unexpected_error(request, exc)

    app.include_router(health_router)
    app.include_router(jobs_router)

    @app.get("/", tags=["health"])
    def root():
        return {"service": "secure-deliberation-backend", "status": "ok", "docs": "/docs", "health": "/healthz"}

    return app


app = create_app()

