"""Jira webhook receipt endpoint."""

import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)

from app.api.dependencies import get_webhook_config, get_webhook_service
from app.api.webhook_common import parse_json_object, process_event, require_string
from app.config.settings import WebhookConfig
from app.core.enums import ServiceType
from app.core.security import validate_shared_secret
from app.schemas.response import WebhookResponse
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/api/v1/webhook", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/jira", response_model=WebhookResponse)
async def receive_jira_webhook(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    config: Annotated[WebhookConfig, Depends(get_webhook_config)],
    webhook_service: Annotated[WebhookService, Depends(get_webhook_service)],
    secret: Annotated[str | None, Header(alias="X-Webhook-Secret")] = None,
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> WebhookResponse:
    """Authenticate and receive a Jira webhook payload."""
    if secret is None or not validate_shared_secret(secret, config.jira_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    payload = await parse_json_object(request)
    event_type = require_string(payload, "webhookEvent")
    logger.info("Jira webhook received: event=%s", event_type)
    result = await process_event(
        webhook_service,
        background_tasks,
        ServiceType.JIRA,
        event_type,
        payload,
        request_id,
    )
    if not result.supported:
        response.status_code = status.HTTP_202_ACCEPTED
        return WebhookResponse(message="Ignored event.")
    if result.duplicate:
        return WebhookResponse(message="Duplicate event ignored.")
    return WebhookResponse(message="Jira webhook processed successfully.")
