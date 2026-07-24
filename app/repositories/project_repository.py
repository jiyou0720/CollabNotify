"""Project persistence operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project


class ProjectRepository:
    """Encapsulate Project database access."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        name: str,
        service: str,
        external_id: str | None = None,
        *,
        discord_guild_id: str | None = None,
        discord_category_id: str | None = None,
    ) -> Project:
        """Create and flush a Project."""
        project = Project(
            name=name,
            service=service,
            external_id=external_id,
            discord_guild_id=discord_guild_id,
            discord_category_id=discord_category_id,
        )
        self._session.add(project)
        self._session.flush()
        return project

    def find_by_id(self, project_id: int) -> Project | None:
        """Find a Project by primary key."""
        return self._session.get(Project, project_id)

    def find_by_name(self, name: str, service: str) -> Project | None:
        """Find a Project by name and service."""
        statement = select(Project).where(
            Project.name == name, Project.service == service
        )
        return self._session.scalar(statement)

    def find_managed(self, name: str, guild_id: int | None = None) -> Project | None:
        """Find one unambiguous Discord-managed logical project."""
        statement = select(Project).where(
            Project.name == name, Project.service == "discord"
        )
        if guild_id is not None:
            statement = statement.where(Project.discord_guild_id == str(guild_id))
            return self._session.scalar(statement)
        matches = list(self._session.scalars(statement.limit(2)))
        return matches[0] if len(matches) == 1 else None

    def list_managed(self, guild_id: int | None = None) -> list[Project]:
        """List Discord-managed projects ordered by creation time."""
        statement = select(Project).where(Project.service == "discord")
        if guild_id is not None:
            statement = statement.where(Project.discord_guild_id == str(guild_id))
        return list(self._session.scalars(statement.order_by(Project.created_at)))

    def update(self, project: Project, **changes: object) -> Project:
        """Update supported Project attributes."""
        allowed = {
            "name",
            "service",
            "external_id",
            "discord_guild_id",
            "discord_category_id",
            "status",
            "enabled",
        }
        for field, value in changes.items():
            if field not in allowed:
                raise ValueError(f"Unsupported Project field: {field}.")
            setattr(project, field, value)
        self._session.flush()
        return project

    def delete(self, project: Project) -> None:
        """Delete a Project and flush cascading mappings."""
        self._session.delete(project)
        self._session.flush()
        self._session.expire_all()
