"""Tests for rotating and redacting log configuration."""

import logging
from pathlib import Path

from app.config.logging import configure_logging


def flush_collabnotify_handlers() -> None:
    """Flush all application-managed logging handlers."""
    for handler in logging.getLogger().handlers:
        if getattr(handler, "collabnotify_handler", False):
            handler.flush()


def test_logging_writes_application_and_error_files(tmp_path: Path) -> None:
    """INFO and ERROR records must be routed to their documented files."""
    configure_logging("INFO", tmp_path)
    logger = logging.getLogger("tests.logging")

    logger.info("startup complete")
    logger.error("notification failed")
    flush_collabnotify_handlers()

    application_log = (tmp_path / "application.log").read_text(encoding="utf-8")
    error_log = (tmp_path / "error.log").read_text(encoding="utf-8")
    assert "startup complete" in application_log
    assert "notification failed" in application_log
    assert "startup complete" not in error_log
    assert "notification failed" in error_log


def test_logging_redacts_labeled_secrets(tmp_path: Path) -> None:
    """Token and Secret values must not appear in rendered logs."""
    configure_logging("INFO", tmp_path)
    logging.getLogger("tests.security").info(
        "token=%s secret=%s authorization=%s",
        "token-value",
        "secret-value",
        "bearer-value",
    )
    flush_collabnotify_handlers()

    content = (tmp_path / "application.log").read_text(encoding="utf-8")
    assert "token-value" not in content
    assert "secret-value" not in content
    assert "bearer-value" not in content
    assert "token=***" in content


def test_logging_redacts_json_style_secrets(tmp_path: Path) -> None:
    """Quoted key/value credentials must also be removed from logs."""
    configure_logging("INFO", tmp_path)
    logging.getLogger("tests.security").info(
        'config={"token": "json-token", "secret":"json-secret"}'
    )
    flush_collabnotify_handlers()

    content = (tmp_path / "application.log").read_text(encoding="utf-8")
    assert "json-token" not in content
    assert "json-secret" not in content


def test_logging_rotates_application_file(tmp_path: Path) -> None:
    """Application logs must rotate when the configured limit is exceeded."""
    configure_logging("INFO", tmp_path, max_bytes=200, backup_count=2)
    logger = logging.getLogger("tests.rotation")
    for index in range(20):
        logger.info("record=%s payload=%s", index, "x" * 50)
    flush_collabnotify_handlers()

    assert (tmp_path / "application.log.1").exists()
