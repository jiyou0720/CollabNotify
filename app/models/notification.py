"""Notification audit log database model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class NotificationLog(Base):
    """Persist one Discord notification delivery attempt."""

    __tablename__ = "notification_logs"
    __table_args__ = (
        UniqueConstraint(
            "service", "external_event_id", name="uq_notification_external_event"
        ),
        Index("idx_notification_event", "event_type"),
        Index("idx_notification_processed", "processed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL")
    )
    external_event_id: Mapped[str | None] = mapped_column(String)
    discord_message_id: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
