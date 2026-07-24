"""Shared inbound webhook request parsing."""

import json
from typing import Any

from fastapi import BackgroundTasks, HTTPException, Request, status

from app.core.enums import ServiceType
from app.services.webhook_service import WebhookProcessResult, WebhookService

MAX_WEBHOOK_BODY_BYTES = 10 * 1024 * 1024


async def read_webhook_body(request: Request) -> bytes:
    """Read a webhook body incrementally while enforcing the size limit."""
    content_length = request.headers.get("Content-Length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Content-Length header.",
            ) from exc
        if declared_length < 0 or declared_length > MAX_WEBHOOK_BODY_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Webhook payload is too large.",
            )

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_WEBHOOK_BODY_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Webhook payload is too large.",
            )
    return bytes(body)


async def parse_json_object(
    request: Request, body: bytes | None = None
) -> dict[str, Any]:
    """Parse a bounded raw request body and require a JSON object payload."""
    if not request.headers.get("User-Agent", "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing User-Agent header.",
        )
    content_type = request.headers.get("Content-Type", "").partition(";")[0].strip()
    if content_type.lower() != "application/json":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content-Type must be application/json.",
        )
    if body is None:
        body = await read_webhook_body(request)
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload must be a JSON object.",
        )
    return payload


def require_string(payload: dict[str, Any], field: str) -> str:
    """Return a required non-empty string field from a payload."""
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing or invalid field: {field}.",
        )
    return value


async def process_event(
    webhook_service: WebhookService,
    background_tasks: BackgroundTasks,
    service: ServiceType,
    event_type: str,
    payload: dict[str, Any],
    external_event_id: str | None = None,
) -> WebhookProcessResult:
    """Normalize now and defer external delivery until after the response."""
    notification = await webhook_service.normalize(service, event_type, payload)
    if notification is None:
        return WebhookProcessResult(supported=False)
    if webhook_service.delivery_enabled:
        background_tasks.add_task(
            webhook_service.deliver_safely, notification, external_event_id
        )
    return WebhookProcessResult(supported=True)
