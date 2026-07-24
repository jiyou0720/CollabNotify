"""Application logging facade."""

import logging

from app.models.error_log import ErrorLog
from app.repositories.error_repository import ErrorRepository


class LoggingService:
    """Provide consistent structured logging and optional DB persistence."""

    def __init__(self, name: str) -> None:
        """Create a logging facade for one component."""
        self._logger = logging.getLogger(name)

    def debug(self, message: str, *args: object) -> None:
        """Write a DEBUG record."""
        self._logger.debug(message, *args)

    def info(self, message: str, *args: object) -> None:
        """Write an INFO record."""
        self._logger.info(message, *args)

    def warning(self, message: str, *args: object) -> None:
        """Write a WARNING record."""
        self._logger.warning(message, *args)

    def error(self, message: str, *args: object, exc_info: bool = False) -> None:
        """Write an ERROR record."""
        self._logger.error(message, *args, exc_info=exc_info)

    @staticmethod
    def save_database_log(
        repository: ErrorRepository,
        *,
        error_code: str,
        message: str,
        service: str | None = None,
        payload: str | None = None,
        stack_trace: str | None = None,
    ) -> ErrorLog:
        """Persist a structured error through the Repository boundary."""
        return repository.save(
            error_code=error_code,
            message=message,
            service=service,
            payload=payload,
            stack_trace=stack_trace,
        )
