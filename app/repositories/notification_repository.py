"""Notification log persistence operations."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.notification import NotificationLog


class NotificationRepository:
    """Encapsulate notification audit and idempotency queries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        service: str,
        event_type: str,
        status: str,
        project_id: int | None = None,
        external_event_id: str | None = None,
        discord_message_id: str | None = None,
    ) -> NotificationLog:
        """Create and flush a notification log."""
        log = NotificationLog(
            service=service,
            event_type=event_type,
            project_id=project_id,
            external_event_id=external_event_id,
            discord_message_id=discord_message_id,
            status=status,
        )
        self._session.add(log)
        self._session.flush()
        return log

    def update_status(
        self,
        log: NotificationLog,
        status: str,
        discord_message_id: str | None = None,
    ) -> NotificationLog:
        """Update a delivery status and optional Discord message ID."""
        log.status = status
        if discord_message_id is not None:
            log.discord_message_id = discord_message_id
        self._session.flush()
        return log

    def exists(self, service: str, external_event_id: str) -> bool:
        """Check whether an external event was already logged."""
        statement = select(NotificationLog.id).where(
            NotificationLog.service == service,
            NotificationLog.external_event_id == external_event_id,
        )
        return self._session.scalar(statement) is not None

    def find_by_external_event(
        self, service: str, external_event_id: str
    ) -> NotificationLog | None:
        """Find a delivery audit record by its provider event identifier."""
        statement = select(NotificationLog).where(
            NotificationLog.service == service,
            NotificationLog.external_event_id == external_event_id,
        )
        return self._session.scalar(statement)

    def claim(
        self,
        *,
        service: str,
        event_type: str,
        project_id: int,
        external_event_id: str | None,
    ) -> NotificationLog | None:
        """Reserve an event, returning None when another request won the race."""
        try:
            with self._session.begin_nested():
                return self.create(
                    service=service,
                    event_type=event_type,
                    project_id=project_id,
                    external_event_id=external_event_id,
                    status="RETRY",
                )
        except IntegrityError:
            return None

    def find_recent(
        self, since: datetime, *, limit: int = 100, offset: int = 0
    ) -> list[NotificationLog]:
        """List a bounded page of notification logs since a timestamp."""
        if limit <= 0 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000.")
        if offset < 0:
            raise ValueError("offset cannot be negative.")
        statement = (
            select(NotificationLog)
            .where(NotificationLog.processed_at >= since)
            .order_by(NotificationLog.processed_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.scalars(statement))

    def find_failed(self) -> list[NotificationLog]:
        """List failed notification logs."""
        statement = select(NotificationLog).where(NotificationLog.status == "FAILED")
        return list(self._session.scalars(statement))
