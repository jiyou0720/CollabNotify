"""HTTP middleware used by the FastAPI application."""

import logging
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class RequestIdMiddleware:
    """Attach a stable request identifier to each HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the ASGI middleware."""
        self._app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Add or generate an X-Request-ID header for HTTP requests."""
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request = Request(scope)
        request_id = request.headers.get("X-Request-ID", "").strip()
        if not request_id or len(request_id) > 128 or not request_id.isprintable():
            request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id

        async def _send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("X-Request-ID", request_id)
            await send(message)

        await self._app(scope, receive, _send_with_request_id)


class RequestLoggingMiddleware:
    """Log HTTP request completion with request ID and duration."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the ASGI middleware."""
        self._app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Record one request completion or failure."""
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        started_at = perf_counter()
        status_code = 500

        async def _capture_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self._app(scope, receive, _capture_status)
        except Exception:
            logger.exception(
                "HTTP request failed: method=%s path=%s",
                scope.get("method"),
                scope.get("path"),
            )
            raise
        finally:
            duration_ms = (perf_counter() - started_at) * 1000
            request_id = scope.get("state", {}).get("request_id", "unknown")
            logger.info(
                "HTTP request completed: method=%s path=%s status=%s "
                "duration_ms=%.2f request_id=%s",
                scope.get("method"),
                scope.get("path"),
                status_code,
                duration_ms,
                request_id,
            )
