import json
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request


logger = logging.getLogger("secure_backend")


class RequestTracingMiddleware:
    def __init__(self, app, request_id_header: str = "X-Request-ID"):
        self.app = app
        self.request_id_header = request_id_header

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        request_id = request.headers.get(self.request_id_header) or str(uuid4())
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id
        started = perf_counter()
        status_container = {"code": 500}

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                status_container["code"] = int(message["status"])
                headers = list(message.get("headers", []))
                headers.append((self.request_id_header.lower().encode("latin-1"), request_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
        duration_ms = round((perf_counter() - started) * 1000, 2)
        logger.info(
            json.dumps(
                {
                    "event": "http_request_completed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_container["code"],
                    "duration_ms": duration_ms,
                }
            )
        )

