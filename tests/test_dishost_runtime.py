"""Tests for the DisHost deployment entry point."""

from unittest.mock import patch

import pytest

from app.hosting.dishost import (
    allocation_port,
    configure_persistent_database,
    ngrok_settings,
)


def test_allocation_port_uses_dishost_precedence() -> None:
    environment = {"PORT": "8000", "SERVER_PORT": "9000", "DISHOST_PORT": "25123"}

    assert allocation_port(environment) == 25123


@pytest.mark.parametrize("value", ["nope", "0", "65536"])
def test_allocation_port_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        allocation_port({"DISHOST_PORT": value})


def test_database_defaults_to_persistent_data_directory() -> None:
    environment = {"DISHOST_DATA_DIR": "/home/container/test-data"}

    with patch("app.hosting.dishost.Path.mkdir") as mkdir:
        result = configure_persistent_database(environment)

    assert result.endswith("/collabnotify.db")
    assert environment["DATABASE_URL"] == result
    mkdir.assert_called_once_with(parents=True, exist_ok=True)


def test_database_preserves_explicit_url() -> None:
    environment = {"DATABASE_URL": "sqlite:///custom.db"}

    assert configure_persistent_database(environment) == "sqlite:///custom.db"


def test_database_prepares_explicit_dishost_data_directory() -> None:
    environment = {
        "DATABASE_URL": "sqlite:////home/container/data/collabnotify.db",
        "DISHOST_DATA_DIR": "/home/container/data",
    }

    with patch("app.hosting.dishost.Path.mkdir") as mkdir:
        result = configure_persistent_database(environment)

    assert result == environment["DATABASE_URL"]
    mkdir.assert_called_once_with(parents=True, exist_ok=True)


def test_ngrok_settings_return_managed_agent_path() -> None:
    token = "secret-token"
    settings = ngrok_settings(
        {
            "NGROK_AUTHTOKEN": token,
            "NGROK_DOMAIN": "example.ngrok-free.app",
            "NGROK_BIN": "/home/container/data/ngrok/ngrok",
        },
    )

    assert settings == (
        token,
        "example.ngrok-free.app",
        "/home/container/data/ngrok/ngrok",
    )


def test_ngrok_requires_token_and_domain_together() -> None:
    with pytest.raises(ValueError, match="must be set together"):
        ngrok_settings({"NGROK_AUTHTOKEN": "secret"})
