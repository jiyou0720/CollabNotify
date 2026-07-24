"""Role mapping persistence operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role_mapping import RoleMapping


class RoleRepository:
    """Encapsulate project-to-Discord role mappings."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self, project_id: int, role_name: str, discord_role_id: str
    ) -> RoleMapping:
        """Create and flush a role mapping."""
        mapping = RoleMapping(
            project_id=project_id,
            role_name=role_name,
            discord_role_id=discord_role_id,
        )
        self._session.add(mapping)
        self._session.flush()
        return mapping

    def find_role(self, project_id: int, role_name: str) -> RoleMapping | None:
        """Find a Discord role mapping by project and name."""
        statement = select(RoleMapping).where(
            RoleMapping.project_id == project_id,
            RoleMapping.role_name == role_name,
        )
        return self._session.scalar(statement)

    def delete(self, mapping: RoleMapping) -> None:
        """Delete a role mapping."""
        self._session.delete(mapping)
        self._session.flush()
