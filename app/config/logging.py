"""Application logging configuration with rotation and redaction."""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
SENSITIVE_PATTERN = re.compile(
    r'(?i)(["\']?(?:token|secret|authorization)["\']?' r'\s*[=:]\s*["\']?)([^\s,"\']+)'
)


class RedactingFormatter(logging.Formatter):
    """Remove labeled credentials from rendered log messages."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a record and replace sensitive values."""
        rendered = super().format(record)
        return SENSITIVE_PATTERN.sub(r"\1***", rendered)


def configure_logging(
    level: str,
    log_dir: str | Path = "logs",
    *,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """Configure console and rotating application/error log files."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    for handler in tuple(root_logger.handlers):
        if getattr(handler, "collabnotify_handler", False):
            root_logger.removeHandler(handler)
            handler.close()

    formatter = RedactingFormatter(LOG_FORMAT)
    handlers: tuple[logging.Handler, ...] = (
        logging.StreamHandler(),
        RotatingFileHandler(
            directory / "application.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        ),
        RotatingFileHandler(
            directory / "error.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        ),
    )
    handlers[0].setLevel(numeric_level)
    handlers[1].setLevel(numeric_level)
    handlers[2].setLevel(logging.ERROR)
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.collabnotify_handler = True  # type: ignore[attr-defined]
        root_logger.addHandler(handler)
