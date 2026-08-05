"""Project alias persistence operations."""

from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project_alias import ProjectAlias


class ProjectAliasRepository:
    """Encapsulate external provider alias persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_alias(
        self, project_id: int, provider: str, external_name: str
    ) -> ProjectAlias:
        """Create and flush an alias."""
        alias = ProjectAlias(
            project_id=project_id,
            provider=provider,
            external_name=external_name,
        )
        self._session.add(alias)
        self._session.flush()
        return alias

    def delete_alias(self, alias: ProjectAlias) -> None:
        """Delete and flush an alias."""
        self._session.delete(alias)
        self._session.flush()

    def find_by_provider(
        self, provider: str, external_name: str
    ) -> ProjectAlias | None:
        """Find an alias using its provider identifier."""
        statement = select(ProjectAlias).where(
            ProjectAlias.provider == provider,
            ProjectAlias.external_name == external_name,
        )
        return self._session.scalar(statement)

    def find_all(self, project_id: int | None = None) -> list[ProjectAlias]:
        """List aliases, optionally limited to one internal project."""
        statement = select(ProjectAlias)
        if project_id is not None:
            statement = statement.where(ProjectAlias.project_id == project_id)
        return list(
            self._session.scalars(
                statement.order_by(ProjectAlias.provider, ProjectAlias.external_name)
            )
        )

    def find_for_projects(self, project_ids: Collection[int]) -> list[ProjectAlias]:
        """List aliases for a set of internal projects in one query."""
        if not project_ids:
            return []
        statement = (
            select(ProjectAlias)
            .where(ProjectAlias.project_id.in_(project_ids))
            .order_by(ProjectAlias.provider, ProjectAlias.external_name)
        )
        return list(self._session.scalars(statement))

    def update_alias(
        self,
        alias: ProjectAlias,
        *,
        project_id: int | None = None,
        provider: str | None = None,
        external_name: str | None = None,
    ) -> ProjectAlias:
        """Update supplied alias fields and flush the change."""
        if project_id is not None:
            alias.project_id = project_id
        if provider is not None:
            alias.provider = provider
        if external_name is not None:
            alias.external_name = external_name
        self._session.flush()
        return alias
