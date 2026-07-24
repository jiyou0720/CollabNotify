"""Static validation for production container configuration."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_uses_python_312_and_non_root_user() -> None:
    """The image must use Python 3.12 and drop root privileges."""
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert dockerfile.startswith("FROM python:3.12-slim")
    assert "USER collabnotify" in dockerfile
    assert 'ENTRYPOINT ["/app/scripts/entrypoint.sh"]' in dockerfile
    assert "HEALTHCHECK" in dockerfile


def test_compose_persists_database_and_logs() -> None:
    """Compose must persist both SQLite data and application logs."""
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "runtime_data:/app/data" in compose
    assert "runtime_logs:/app/logs" in compose
    assert "runtime_data:" in compose
    assert "runtime_logs:" in compose
    assert "sqlite:////app/data/collabnotify.db" in compose
    assert "./database:/app/database" not in compose
    assert "./logs:/app/logs" not in compose
    assert "restart: unless-stopped" in compose


def test_docker_context_excludes_credentials() -> None:
    """Local credentials must never enter the Docker build context."""
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert ".env\n" in dockerignore
    assert ".venv" in dockerignore
