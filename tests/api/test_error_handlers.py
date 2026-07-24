"""Tests for global FastAPI error responses."""

from fastapi import Depends
from fastapi.testclient import TestClient

from app.api.dependencies import get_webhook_config
from app.config.settings import WebhookConfig
from app.main import create_app


def test_http_exception_uses_common_error_body() -> None:
    """Webhook authentication failures must use the common error schema."""
    application = create_app()
    application.dependency_overrides[get_webhook_config] = lambda: WebhookConfig(
        github_secret="github-secret",
        jira_secret="jira-secret",
        confluence_secret="confluence-secret",
    )
    with TestClient(application) as client:
        response = client.post("/api/v1/webhook/github", json={})

    assert response.status_code == 401
    assert response.json() == {"success": False, "error": "Invalid signature."}


def test_dependency_validation_uses_bad_request() -> None:
    """FastAPI validation errors must be normalized to HTTP 400."""
    application = create_app()

    def require_number(number: int) -> int:
        return number

    @application.get("/validation-test")
    async def validation_test(number: int = Depends(require_number)) -> dict[str, int]:
        return {"number": number}

    with TestClient(application) as client:
        response = client.get("/validation-test", params={"number": "invalid"})

    assert response.status_code == 400
    assert response.json() == {"success": False, "error": "Invalid request."}


def test_unexpected_exception_hides_internal_details() -> None:
    """Unexpected errors must not expose exception details."""
    application = create_app()

    @application.get("/failure-test")
    async def failure_test() -> None:
        raise RuntimeError("sensitive internal detail")

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/failure-test")

    assert response.status_code == 500
    assert response.json() == {
        "success": False,
        "error": "Internal server error.",
    }
    assert "sensitive" not in response.text
