"""Discord review thread database model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class ReviewThread(Base):
    """Track one Discord discussion thread for an external resource."""

    __tablename__ = "review_threads"
    __table_args__ = (
        UniqueConstraint(
            "service", "external_resource_id", name="uq_review_service_resource"
        ),
        Index("idx_review_thread_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    service: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    external_resource_id: Mapped[str] = mapped_column(String, nullable=False)
    discord_message_id: Mapped[str] = mapped_column(String, nullable=False)
    discord_thread_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="IN_REVIEW", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
