"""Discord project server lifecycle management."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

import discord
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import InvalidConfigurationError
from app.models.channel import ChannelMapping
from app.models.project import Project
from app.repositories.channel_repository import ChannelRepository
from app.repositories.project_repository import ProjectRepository
from database.session import session_scope

DEFAULT_PROJECT_CHANNELS = (
    "general",
    "github",
    "jira",
    "confluence",
    "meeting",
    "release",
)
ARCHIVE_CATEGORY_NAME = "📦 Archived"


@dataclass(frozen=True, slots=True)
class ManagedProjectResult:
    """Discord resources created or resolved for a managed project."""

    project: Project
    category: discord.CategoryChannel
    channels: dict[str, discord.TextChannel]


class ProjectManagementService:
    """Create, map, archive, restore, and delete Discord project spaces."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._logger = logging.getLogger(__name__)

    async def create_project(
        self, guild: discord.Guild, project_name: str
    ) -> ManagedProjectResult:
        """Create a category, default channels, and their database mappings."""
        name = self._validate_project_name(project_name)
        with session_scope(self._session_factory) as session:
            if ProjectRepository(session).find_managed(name, guild.id) is not None:
                raise InvalidConfigurationError("이미 등록된 프로젝트입니다.")

        category: discord.CategoryChannel | None = None
        channels: dict[str, discord.TextChannel] = {}
        try:
            category = await guild.create_category(
                name, reason="CollabNotify 프로젝트 생성"
            )
            for channel_name in DEFAULT_PROJECT_CHANNELS:
                channels[channel_name] = await guild.create_text_channel(
                    channel_name,
                    category=category,
                    reason="CollabNotify 기본 채널 생성",
                )

            with session_scope(self._session_factory) as session:
                projects = ProjectRepository(session)
                project = projects.create(
                    name,
                    "discord",
                    self._external_id(guild.id, name),
                    discord_guild_id=str(guild.id),
                    discord_category_id=str(category.id),
                )
                mappings = ChannelRepository(session)
                for service, channel in channels.items():
                    mappings.create(
                        service,
                        project.id,
                        str(channel.id),
                        channel.name,
                    )
        except Exception:
            await self._cleanup_created_resources(category, channels.values())
            raise

        self._logger.info(
            "Managed Discord project created: guild_id=%s project=%s",
            guild.id,
            name,
        )
        return ManagedProjectResult(project, category, channels)

    async def delete_project(self, guild: discord.Guild, project_name: str) -> None:
        """Delete Discord resources and all project-owned database records."""
        with session_scope(self._session_factory) as session:
            projects = ProjectRepository(session)
            project = self._require_project(projects, guild.id, project_name)
            mappings = ChannelRepository(session).list_for_project(project.id)
            channel_ids = [int(mapping.discord_channel_id) for mapping in mappings]
            category_id = self._parse_id(project.discord_category_id, "category")

        for channel_id in channel_ids:
            channel = guild.get_channel(channel_id)
            if channel is not None:
                await channel.delete(reason="CollabNotify 프로젝트 삭제")
        category = guild.get_channel(category_id)
        if isinstance(category, discord.CategoryChannel):
            await category.delete(reason="CollabNotify 프로젝트 삭제")

        with session_scope(self._session_factory) as session:
            projects = ProjectRepository(session)
            project = self._require_project(projects, guild.id, project_name)
            projects.delete(project)
        self._logger.info(
            "Managed Discord project deleted: guild_id=%s project=%s",
            guild.id,
            project_name,
        )

    async def archive_project(self, guild: discord.Guild, project_name: str) -> Project:
        """Move project channels to the shared archive and disable delivery."""
        with session_scope(self._session_factory) as session:
            projects = ProjectRepository(session)
            project = self._require_project(projects, guild.id, project_name)
            if project.status == "ARCHIVED":
                raise InvalidConfigurationError("이미 보관된 프로젝트입니다.")
            channel_ids = [
                int(mapping.discord_channel_id)
                for mapping in ChannelRepository(session).list_for_project(project.id)
            ]

        archive = discord.utils.get(guild.categories, name=ARCHIVE_CATEGORY_NAME)
        if archive is None:
            archive = await guild.create_category(
                ARCHIVE_CATEGORY_NAME, reason="CollabNotify 보관함 생성"
            )
        for channel_id in channel_ids:
            channel = guild.get_channel(channel_id)
            if isinstance(channel, discord.TextChannel):
                await channel.edit(
                    category=archive, reason="CollabNotify 프로젝트 보관"
                )

        with session_scope(self._session_factory) as session:
            projects = ProjectRepository(session)
            project = self._require_project(projects, guild.id, project_name)
            projects.update(project, status="ARCHIVED", enabled=False)
            return project

    async def restore_project(self, guild: discord.Guild, project_name: str) -> Project:
        """Move archived channels back to their project category."""
        with session_scope(self._session_factory) as session:
            projects = ProjectRepository(session)
            project = self._require_project(projects, guild.id, project_name)
            if project.status != "ARCHIVED":
                raise InvalidConfigurationError("보관된 프로젝트가 아닙니다.")
            channel_ids = [
                int(mapping.discord_channel_id)
                for mapping in ChannelRepository(session).list_for_project(project.id)
            ]
            category_id = self._parse_id(project.discord_category_id, "category")

        category = guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            category = discord.utils.get(guild.categories, name=project_name.strip())
            if category is None:
                category = await guild.create_category(
                    project_name.strip(), reason="CollabNotify 프로젝트 복원"
                )
        for channel_id in channel_ids:
            channel = guild.get_channel(channel_id)
            if isinstance(channel, discord.TextChannel):
                await channel.edit(
                    category=category, reason="CollabNotify 프로젝트 복원"
                )

        with session_scope(self._session_factory) as session:
            projects = ProjectRepository(session)
            project = self._require_project(projects, guild.id, project_name)
            projects.update(
                project,
                discord_category_id=str(category.id),
                status="ACTIVE",
                enabled=True,
            )
            return project

    def list_projects(self, guild_id: int) -> list[Project]:
        """List all managed projects for one guild."""
        with session_scope(self._session_factory) as session:
            return ProjectRepository(session).list_managed(guild_id)

    def project_info(
        self, guild_id: int, project_name: str
    ) -> tuple[Project, list[ChannelMapping]]:
        """Return one project and its detached channel mappings."""
        with session_scope(self._session_factory) as session:
            projects = ProjectRepository(session)
            project = self._require_project(projects, guild_id, project_name)
            mappings = ChannelRepository(session).list_for_project(project.id)
            return project, list(mappings)

    def map_channel(
        self,
        guild_id: int,
        project_name: str,
        service: str,
        channel: discord.TextChannel,
    ) -> None:
        """Create or replace a service channel mapping."""
        normalized_service = self._validate_service(service)
        if channel.guild.id != guild_id:
            raise InvalidConfigurationError("다른 서버의 채널은 연결할 수 없습니다.")
        with session_scope(self._session_factory) as session:
            projects = ProjectRepository(session)
            project = self._require_project(projects, guild_id, project_name)
            ChannelRepository(session).set_channel(
                normalized_service,
                project.id,
                str(channel.id),
                channel.name,
            )

    def unmap_channel(self, guild_id: int, project_name: str, service: str) -> bool:
        """Remove one service channel mapping."""
        normalized_service = self._validate_service(service)
        with session_scope(self._session_factory) as session:
            projects = ProjectRepository(session)
            project = self._require_project(projects, guild_id, project_name)
            return ChannelRepository(session).delete_service(
                normalized_service, project.id
            )

    @staticmethod
    def _require_project(
        repository: ProjectRepository, guild_id: int, project_name: str
    ) -> Project:
        project = repository.find_managed(project_name.strip(), guild_id)
        if project is None:
            raise InvalidConfigurationError("프로젝트를 찾을 수 없습니다.")
        return project

    @staticmethod
    def _validate_project_name(project_name: str) -> str:
        name = project_name.strip()
        if not name or len(name) > 80:
            raise ValueError("프로젝트명은 1자 이상 80자 이하여야 합니다.")
        if any(character in name for character in "\r\n"):
            raise ValueError("프로젝트명에 줄바꿈을 사용할 수 없습니다.")
        return name

    @staticmethod
    def _validate_service(service: str) -> str:
        normalized = service.strip().lower()
        if normalized not in DEFAULT_PROJECT_CHANNELS:
            raise ValueError("지원하지 않는 채널 종류입니다.")
        return normalized

    @staticmethod
    def _external_id(guild_id: int, project_name: str) -> str:
        return f"discord:{guild_id}:{project_name.casefold()}"

    @staticmethod
    def _parse_id(value: str | None, resource: str) -> int:
        try:
            identifier = int(value or "")
        except ValueError as exc:
            raise InvalidConfigurationError(
                f"Discord {resource} ID가 올바르지 않습니다."
            ) from exc
        return identifier

    @staticmethod
    async def _cleanup_created_resources(
        category: discord.CategoryChannel | None,
        channels: Iterable[discord.TextChannel],
    ) -> None:
        for channel in reversed(list(channels)):
            try:
                await channel.delete(reason="CollabNotify 생성 롤백")
            except discord.HTTPException:
                logging.getLogger(__name__).exception(
                    "Failed to roll back a Discord project channel."
                )
        if category is not None:
            try:
                await category.delete(reason="CollabNotify 생성 롤백")
            except discord.HTTPException:
                logging.getLogger(__name__).exception(
                    "Failed to roll back a Discord project category."
                )
