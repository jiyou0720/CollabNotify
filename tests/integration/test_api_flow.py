"""Authenticated API-to-Handler integration tests."""

import hashlib
import hmac
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_event_dispatcher,
    get_webhook_config,
    get_webhook_service,
)
from app.config.settings import WebhookConfig
from app.main import create_app
from app.services.webhook_service import NotificationCoordinator, WebhookService


def test_signed_github_request_reaches_production_handler() -> None:
    """A signed API request must pass through the real Dispatcher registry."""
    config = WebhookConfig(
        github_secret="secret",
        jira_secret="secret",
        confluence_secret="secret",
    )
    body = (
        b'{"action":"opened","repository":{"full_name":"org/repo"},'
        b'"issue":{"number":1,"title":"Issue"}}'
    )
    digest = hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    application = create_app()
    application.dependency_overrides[get_webhook_config] = lambda: config

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/webhook/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "issues",
                "X-GitHub-Delivery": "delivery-api-1",
                "X-Hub-Signature-256": f"sha256={digest}",
            },
        )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_api_defers_enabled_notification_delivery() -> None:
    """API orchestration must schedule delivery as a background task."""
    config = WebhookConfig(
        github_secret="secret",
        jira_secret="secret",
        confluence_secret="secret",
    )
    body = (
        b'{"action":"opened","repository":{"full_name":"org/repo"},'
        b'"issue":{"number":1,"title":"Issue"}}'
    )
    digest = hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    coordinator = Mock(spec=NotificationCoordinator)
    coordinator.deliver = AsyncMock(return_value=True)
    get_event_dispatcher.cache_clear()
    webhook_service = WebhookService(get_event_dispatcher(), coordinator)
    application = create_app()
    application.dependency_overrides[get_webhook_config] = lambda: config
    application.dependency_overrides[get_webhook_service] = lambda: webhook_service

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/webhook/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "issues",
                "X-GitHub-Delivery": "delivery-api-2",
                "X-Hub-Signature-256": f"sha256={digest}",
            },
        )

    assert response.status_code == 200
    coordinator.deliver.assert_awaited_once()
