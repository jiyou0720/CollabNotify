"""Structured Confluence document change request."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class ChangeRequest(Base):
    """Track a Discord-originated request until its author confirms it."""

    __tablename__ = "change_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    review_thread_id: Mapped[int] = mapped_column(
        ForeignKey("review_threads.id", ondelete="CASCADE"), nullable=False
    )
    requester_discord_id: Mapped[str] = mapped_column(String, nullable=False)
    requester_name: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String, default="OPEN", nullable=False)
    requested_page_version: Mapped[int | None] = mapped_column(Integer)
    detected_page_version: Mapped[int | None] = mapped_column(Integer)
    confluence_comment_id: Mapped[str | None] = mapped_column(String)
    discord_message_id: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
