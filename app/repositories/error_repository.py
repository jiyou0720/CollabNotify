"""Error log persistence operations."""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.error_log import ErrorLog


class ErrorRepository:
    """Encapsulate structured error log access."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(
        self,
        *,
        error_code: str,
        message: str,
        service: str | None = None,
        payload: str | None = None,
        stack_trace: str | None = None,
    ) -> ErrorLog:
        """Create and flush an error log."""
        log = ErrorLog(
            error_code=error_code,
            service=service,
            message=message,
            payload=payload,
            stack_trace=stack_trace,
        )
        self._session.add(log)
        self._session.flush()
        return log

    def find_all(self) -> list[ErrorLog]:
        """List errors in reverse chronological order."""
        statement = select(ErrorLog).order_by(ErrorLog.created_at.desc())
        return list(self._session.scalars(statement))

    def delete_old(self, before: datetime) -> int:
        """Delete errors older than the retention boundary."""
        result = self._session.execute(
            delete(ErrorLog).where(ErrorLog.created_at < before)
        )
        return result.rowcount or 0
