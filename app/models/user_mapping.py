"""External user to Discord user mapping model."""

from datetime import datetime

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class UserMapping(Base):
    """Map a service username to a Discord user."""

    __tablename__ = "user_mappings"
    __table_args__ = (
        UniqueConstraint(
            "service", "external_username", name="uq_user_service_username"
        ),
        Index("idx_user_service", "service", "external_username"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String, nullable=False)
    external_username: Mapped[str] = mapped_column(String, nullable=False)
    discord_user_id: Mapped[str] = mapped_column(String, nullable=False)
    discord_display_name: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
