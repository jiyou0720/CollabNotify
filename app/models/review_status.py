"""Review status history database model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class ReviewStatus(Base):
    """Record one status transition for a review thread."""

    __tablename__ = "review_statuses"
    __table_args__ = (Index("idx_review_status_thread", "review_thread_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    review_thread_id: Mapped[int] = mapped_column(
        ForeignKey("review_threads.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    changed_by_discord_id: Mapped[str | None] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
