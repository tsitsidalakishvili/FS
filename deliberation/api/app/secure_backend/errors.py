from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .schemas import ErrorBody, ErrorResponse


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict[str, Any] | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error_payload(code: str, message: str, request: Request, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return ErrorResponse(error=ErrorBody(code=code, message=message, details=details, request_id=_request_id(request))).model_dump()


async def handle_app_error(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(exc.code, exc.message, request, exc.details),
    )


async def handle_http_exception(request: Request, exc: HTTPException):
    message = str(exc.detail) if exc.detail else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload("http_error", message, request),
    )


async def handle_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=_error_payload(
            "validation_error",
            "Invalid request payload",
            request,
            {"errors": exc.errors()},
        ),
    )


async def handle_unexpected_error(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=_error_payload("internal_error", "Unexpected server error", request),
    )

