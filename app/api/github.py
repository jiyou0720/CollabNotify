"""GitHub webhook receipt endpoint."""

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
from app.api.webhook_common import parse_json_object, process_event, read_webhook_body
from app.config.settings import WebhookConfig
from app.core.enums import ServiceType
from app.core.security import validate_github_signature
from app.schemas.response import WebhookResponse
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/api/v1/webhook", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/github", response_model=WebhookResponse)
async def receive_github_webhook(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    config: Annotated[WebhookConfig, Depends(get_webhook_config)],
    webhook_service: Annotated[WebhookService, Depends(get_webhook_service)],
    event_type: Annotated[str | None, Header(alias="X-GitHub-Event")] = None,
    signature: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
    delivery_id: Annotated[str | None, Header(alias="X-GitHub-Delivery")] = None,
) -> WebhookResponse:
    """Authenticate and receive a GitHub webhook payload."""
    body = await read_webhook_body(request)
    if signature is None or not validate_github_signature(
        body, signature, config.github_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature.",
        )
    if event_type is None or not event_type.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-GitHub-Event header.",
        )

    payload = await parse_json_object(request, body)
    logger.info("GitHub webhook received: event=%s", event_type)
    result = await process_event(
        webhook_service,
        background_tasks,
        ServiceType.GITHUB,
        event_type,
        payload,
        delivery_id,
    )
    if not result.supported:
        response.status_code = status.HTTP_202_ACCEPTED
        return WebhookResponse(message="Ignored event.")
    if result.duplicate:
        return WebhookResponse(message="Duplicate event ignored.")
    return WebhookResponse(message="GitHub webhook processed successfully.")
