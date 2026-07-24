"""API tests for inbound webhook receipt."""

import hashlib
import hmac

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api.dependencies import get_event_dispatcher, get_webhook_config
from app.api.webhook_common import MAX_WEBHOOK_BODY_BYTES, read_webhook_body
from app.config.settings import WebhookConfig
from app.core.enums import ServiceType
from app.dispatcher.dispatcher import EventDispatcher
from app.main import create_app
from app.schemas.common import Notification

TEST_CONFIG = WebhookConfig(
    github_secret="github-secret",
    jira_secret="jira-secret",
    confluence_secret="confluence-secret",
)


class AcceptingHandler:
    """Test Handler that accepts every registered payload."""

    async def handle(self, payload: dict[str, object]) -> object:
        """Return a normalized Notification without side effects."""
        return Notification(
            service=ServiceType.GITHUB,
            event_type="test",
            title="Test",
            description="Test notification.",
            fields=(),
        )


def create_test_app() -> FastAPI:
    """Create an API application with deterministic webhook secrets."""
    application = create_app()
    application.dependency_overrides[get_webhook_config] = lambda: TEST_CONFIG
    dispatcher = EventDispatcher()
    handler = AcceptingHandler()
    dispatcher.register(ServiceType.GITHUB, "issues", handler)
    dispatcher.register(ServiceType.JIRA, "jira:issue_created", handler)
    dispatcher.register(ServiceType.CONFLUENCE, "page_created", handler)
    application.dependency_overrides[get_event_dispatcher] = lambda: dispatcher
    return application


def github_signature(body: bytes) -> str:
    """Create a valid signature for the test GitHub secret."""
    digest = hmac.new(
        TEST_CONFIG.github_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return f"sha256={digest}"


def test_github_webhook_accepts_valid_request() -> None:
    """A signed GitHub JSON payload must be accepted."""
    body = b'{"action":"opened"}'
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "issues",
        "X-Hub-Signature-256": github_signature(body),
    }

    with TestClient(create_test_app()) as client:
        response = client.post("/api/v1/webhook/github", content=body, headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "GitHub webhook processed successfully.",
    }


def test_github_webhook_rejects_invalid_signature() -> None:
    """An invalid GitHub signature must return HTTP 401."""
    with TestClient(create_test_app()) as client:
        response = client.post(
            "/api/v1/webhook/github",
            json={"action": "opened"},
            headers={
                "X-GitHub-Event": "issues",
                "X-Hub-Signature-256": "sha256=invalid",
            },
        )

    assert response.status_code == 401


def test_github_webhook_rejects_missing_event_header() -> None:
    """A signed request still requires the GitHub event header."""
    body = b'{"action":"opened"}'
    with TestClient(create_test_app()) as client:
        response = client.post(
            "/api/v1/webhook/github",
            content=body,
            headers={"X-Hub-Signature-256": github_signature(body)},
        )

    assert response.status_code == 400


def test_jira_webhook_accepts_valid_request() -> None:
    """An authenticated Jira event must be accepted."""
    with TestClient(create_test_app()) as client:
        response = client.post(
            "/api/v1/webhook/jira",
            json={"webhookEvent": "jira:issue_created", "issue": {}},
            headers={"X-Webhook-Secret": TEST_CONFIG.jira_secret},
        )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_confluence_webhook_accepts_valid_request() -> None:
    """An authenticated Confluence event must be accepted."""
    with TestClient(create_test_app()) as client:
        response = client.post(
            "/api/v1/webhook/confluence",
            json={"eventType": "page_created", "page": {}},
            headers={"X-Webhook-Secret": TEST_CONFIG.confluence_secret},
        )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_atlassian_webhooks_reject_invalid_secret() -> None:
    """Jira and Confluence must reject an invalid shared secret."""
    with TestClient(create_test_app()) as client:
        jira_response = client.post(
            "/api/v1/webhook/jira",
            json={"webhookEvent": "jira:issue_created"},
            headers={"X-Webhook-Secret": "invalid"},
        )
        confluence_response = client.post(
            "/api/v1/webhook/confluence",
            json={"eventType": "page_created"},
            headers={"X-Webhook-Secret": "invalid"},
        )

    assert jira_response.status_code == 401
    assert confluence_response.status_code == 401


def test_webhook_rejects_invalid_json() -> None:
    """Authenticated non-JSON input must return HTTP 400."""
    with TestClient(create_test_app()) as client:
        response = client.post(
            "/api/v1/webhook/jira",
            content=b"not-json",
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Secret": TEST_CONFIG.jira_secret,
            },
        )

    assert response.status_code == 400


def test_webhook_requires_json_content_type() -> None:
    """Webhook endpoints must enforce the documented content type."""
    with TestClient(create_test_app()) as client:
        response = client.post(
            "/api/v1/webhook/jira",
            content=b'{"webhookEvent":"jira:issue_created"}',
            headers={"X-Webhook-Secret": TEST_CONFIG.jira_secret},
        )

    assert response.status_code == 400


def test_webhook_rejects_missing_user_agent() -> None:
    """The common API contract requires sender identification."""
    with TestClient(create_test_app()) as client:
        response = client.post(
            "/api/v1/webhook/jira",
            content=b'{"webhookEvent":"jira:issue_created"}',
            headers={
                "Content-Type": "application/json",
                "User-Agent": "",
                "X-Webhook-Secret": TEST_CONFIG.jira_secret,
            },
        )

    assert response.status_code == 400


def test_webhook_rejects_oversized_declared_payload() -> None:
    """Unbounded request bodies must be rejected before JSON parsing."""
    with TestClient(create_test_app()) as client:
        response = client.post(
            "/api/v1/webhook/jira",
            content=b"{}",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(MAX_WEBHOOK_BODY_BYTES + 1),
                "X-Webhook-Secret": TEST_CONFIG.jira_secret,
            },
        )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_webhook_stream_limit_without_content_length() -> None:
    """Chunked bodies must be bounded even without Content-Length."""
    messages = iter(
        (
            {
                "type": "http.request",
                "body": b"x" * MAX_WEBHOOK_BODY_BYTES,
                "more_body": True,
            },
            {"type": "http.request", "body": b"x", "more_body": False},
        )
    )

    async def receive() -> dict[str, object]:
        return next(messages)

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/webhook/github",
            "headers": [],
        },
        receive,
    )

    with pytest.raises(HTTPException) as captured:
        await read_webhook_body(request)

    assert captured.value.status_code == 413


def test_webhook_rejects_missing_event_field() -> None:
    """Atlassian payloads must identify their event type."""
    with TestClient(create_test_app()) as client:
        response = client.post(
            "/api/v1/webhook/confluence",
            json={"page": {}},
            headers={"X-Webhook-Secret": TEST_CONFIG.confluence_secret},
        )

    assert response.status_code == 400


def test_webhook_returns_accepted_for_unsupported_event() -> None:
    """Valid but unregistered events must be ignored with HTTP 202."""
    with TestClient(create_test_app()) as client:
        response = client.post(
            "/api/v1/webhook/jira",
            json={"webhookEvent": "jira:unsupported"},
            headers={"X-Webhook-Secret": TEST_CONFIG.jira_secret},
        )

    assert response.status_code == 202
    assert response.json() == {"success": True, "message": "Ignored event."}
