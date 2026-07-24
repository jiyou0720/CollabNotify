"""Tests for the FastAPI application and health endpoint."""

from fastapi.testclient import TestClient

from app.api.dependencies import get_health_status
from app.main import create_app


def test_health_check_returns_ok() -> None:
    """The health endpoint must return the documented response."""
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_health_check_preserves_request_id() -> None:
    """Middleware must preserve a caller-provided request identifier."""
    with TestClient(create_app()) as client:
        response = client.get("/health", headers={"X-Request-ID": "request-123"})

    assert response.headers["X-Request-ID"] == "request-123"


def test_health_dependency_can_be_overridden() -> None:
    """Application dependencies must be replaceable during tests."""
    application = create_app()
    application.dependency_overrides[get_health_status] = lambda: "degraded"

    with TestClient(application) as client:
        response = client.get("/health")

    assert response.json() == {"status": "degraded"}


def test_openapi_and_swagger_are_enabled() -> None:
    """Default OpenAPI and Swagger endpoints must be available."""
    with TestClient(create_app()) as client:
        openapi_response = client.get("/openapi.json")
        swagger_response = client.get("/docs")

    assert openapi_response.status_code == 200
    assert "/health" in openapi_response.json()["paths"]
    assert swagger_response.status_code == 200
