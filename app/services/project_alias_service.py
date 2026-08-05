"""External provider alias application service."""

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import InvalidConfigurationError
from app.models.project_alias import ProjectAlias
from app.repositories.project_alias_repository import ProjectAliasRepository
from app.repositories.project_repository import ProjectRepository
from database.session import session_scope

SUPPORTED_ALIAS_PROVIDERS = frozenset({"github", "jira", "confluence"})


@dataclass(frozen=True, slots=True)
class ProjectAliasView:
    """Detached alias details safe for command and delivery consumers."""

    id: int
    project_id: int
    project_name: str
    provider: str
    external_name: str


class ProjectAliasService:
    """Manage and resolve provider identifiers for internal projects."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_alias(
        self,
        guild_id: int,
        provider: str,
        external_name: str,
        project_name: str,
    ) -> ProjectAliasView:
        """Create a provider alias for a guild-owned internal project."""
        normalized_provider, normalized_name = self._normalize(provider, external_name)
        with session_scope(self._session_factory) as session:
            aliases = ProjectAliasRepository(session)
            if aliases.find_by_provider(normalized_provider, normalized_name):
                raise InvalidConfigurationError("이미 등록된 외부 프로젝트 별칭입니다.")
            project = ProjectRepository(session).find_managed(
                project_name.strip(), guild_id
            )
            if project is None:
                raise InvalidConfigurationError("내부 프로젝트를 찾을 수 없습니다.")
            alias = aliases.create_alias(
                project.id, normalized_provider, normalized_name
            )
            return self._view(alias, project.name)

    def delete_alias(self, guild_id: int, provider: str, external_name: str) -> bool:
        """Delete a provider alias only when it belongs to the guild."""
        normalized_provider, normalized_name = self._normalize(provider, external_name)
        with session_scope(self._session_factory) as session:
            aliases = ProjectAliasRepository(session)
            alias = aliases.find_by_provider(normalized_provider, normalized_name)
            if alias is None:
                return False
            project = ProjectRepository(session).find_by_id(alias.project_id)
            if project is None or project.discord_guild_id != str(guild_id):
                return False
            aliases.delete_alias(alias)
            return True

    def find_by_provider(
        self, provider: str, external_name: str
    ) -> ProjectAliasView | None:
        """Resolve a provider identifier to an internal project."""
        normalized_provider, normalized_name = self._normalize(provider, external_name)
        with session_scope(self._session_factory) as session:
            alias = ProjectAliasRepository(session).find_by_provider(
                normalized_provider, normalized_name
            )
            if alias is None:
                return None
            project = ProjectRepository(session).find_by_id(alias.project_id)
            if project is None or project.service != "discord":
                return None
            return self._view(alias, project.name)

    def find_all(self, guild_id: int) -> list[ProjectAliasView]:
        """List aliases owned by one Discord guild."""
        with session_scope(self._session_factory) as session:
            projects = {
                project.id: project.name
                for project in ProjectRepository(session).list_managed(guild_id)
            }
            return [
                self._view(alias, projects[alias.project_id])
                for alias in ProjectAliasRepository(session).find_for_projects(
                    projects.keys()
                )
            ]

    def update_alias(
        self,
        guild_id: int,
        provider: str,
        external_name: str,
        *,
        new_provider: str | None = None,
        new_external_name: str | None = None,
        project_name: str | None = None,
    ) -> ProjectAliasView:
        """Update an existing guild-owned alias."""
        old_provider, old_name = self._normalize(provider, external_name)
        target_provider, target_name = self._normalize(
            new_provider or provider, new_external_name or external_name
        )
        with session_scope(self._session_factory) as session:
            aliases = ProjectAliasRepository(session)
            alias = aliases.find_by_provider(old_provider, old_name)
            if alias is None:
                raise InvalidConfigurationError(
                    "외부 프로젝트 별칭을 찾을 수 없습니다."
                )
            current = ProjectRepository(session).find_by_id(alias.project_id)
            if current is None or current.discord_guild_id != str(guild_id):
                raise InvalidConfigurationError(
                    "외부 프로젝트 별칭을 찾을 수 없습니다."
                )
            project = current
            if project_name is not None:
                project = ProjectRepository(session).find_managed(
                    project_name.strip(), guild_id
                )
                if project is None:
                    raise InvalidConfigurationError("내부 프로젝트를 찾을 수 없습니다.")
            duplicate = aliases.find_by_provider(target_provider, target_name)
            if duplicate is not None and duplicate.id != alias.id:
                raise InvalidConfigurationError("이미 등록된 외부 프로젝트 별칭입니다.")
            aliases.update_alias(
                alias,
                project_id=project.id,
                provider=target_provider,
                external_name=target_name,
            )
            return self._view(alias, project.name)

    @staticmethod
    def _normalize(provider: str, external_name: str) -> tuple[str, str]:
        normalized_provider = provider.strip().lower()
        if normalized_provider not in SUPPORTED_ALIAS_PROVIDERS:
            raise ValueError("지원하지 않는 제공자입니다: github, jira, confluence")
        normalized_name = external_name.strip()
        if not normalized_name or len(normalized_name) > 255:
            raise ValueError("외부 프로젝트 이름은 1자 이상 255자 이하여야 합니다.")
        if "\n" in normalized_name or "\r" in normalized_name:
            raise ValueError("외부 프로젝트 이름에 줄바꿈을 사용할 수 없습니다.")
        if normalized_provider == "github":
            normalized_name = normalized_name.casefold()
        return normalized_provider, normalized_name

    @staticmethod
    def _view(alias: ProjectAlias, project_name: str) -> ProjectAliasView:
        return ProjectAliasView(
            id=alias.id,
            project_id=alias.project_id,
            project_name=project_name,
            provider=alias.provider,
            external_name=alias.external_name,
        )
