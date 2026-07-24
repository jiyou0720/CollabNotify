"""Discord role mapping database model."""

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RoleMapping(Base):
    """Map a project role name to a Discord role."""

    __tablename__ = "role_mappings"
    __table_args__ = (
        UniqueConstraint("project_id", "role_name", name="uq_role_project_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    role_name: Mapped[str] = mapped_column(String, nullable=False)
    discord_role_id: Mapped[str] = mapped_column(String, nullable=False)
