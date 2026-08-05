"""One Discord user's completion of a document review."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class ReviewCompletion(Base):
    """Persist an idempotent review-complete interaction."""

    __tablename__ = "review_completions"
    __table_args__ = (
        UniqueConstraint(
            "review_thread_id", "discord_user_id", name="uq_review_completion_user"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    review_thread_id: Mapped[int] = mapped_column(
        ForeignKey("review_threads.id", ondelete="CASCADE"), nullable=False
    )
    discord_user_id: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    confluence_comment_id: Mapped[str | None] = mapped_column(String)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
