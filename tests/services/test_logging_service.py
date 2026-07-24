"""Tests for the LoggingService facade."""

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.config.logging import configure_logging
from app.repositories.error_repository import ErrorRepository
from app.services.logging_service import LoggingService


def test_logging_service_writes_component_records(tmp_path: Path) -> None:
    """The facade must delegate records to configured handlers."""
    configure_logging("DEBUG", tmp_path)
    service = LoggingService("tests.component")

    service.debug("debug record")
    service.info("info record")
    service.warning("warning record")
    service.error("error record")
    for handler in logging.getLogger().handlers:
        handler.flush()

    content = (tmp_path / "application.log").read_text(encoding="utf-8")
    assert "debug record" in content
    assert "error record" in content


def test_logging_service_persists_error(db_session: Session) -> None:
    """Database error logging must remain behind the Repository boundary."""
    error = LoggingService.save_database_log(
        ErrorRepository(db_session),
        error_code="SYS001",
        message="Internal failure",
        service="system",
    )

    assert error.id is not None
    assert error.error_code == "SYS001"
