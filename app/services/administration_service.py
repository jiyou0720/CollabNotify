"""Discord administration and settings operations."""

from __future__ import annotations

from dataclasses import dataclass

import discord
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import InvalidConfigurationError
from app.repositories.channel_repository import ChannelRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.review_thread_repository import ReviewThreadRepository
from app.repositories.reviewer_repository import ReviewerRepository
from app.repositories.setting_repository import SettingRepository
from database.session import session_scope


@dataclass(frozen=True, slots=True)
class AdministrationStatus:
    """Current operating status shown to a Discord administrator."""

    project_count: int
    open_review_count: int
    latency_ms: int
    database_ok: bool


class AdministrationService:
    """Provide cleanup, status, and persistent Discord settings."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def cleanup(self, guild: discord.Guild) -> int:
        """Remove channel mappings whose Discord resources no longer exist."""
        removed = 0
        with session_scope(self._session_factory) as session:
            projects = ProjectRepository(session)
            channels = ChannelRepository(session)
            for project in projects.list_managed(guild.id):
                for mapping in channels.list_for_project(project.id):
                    if guild.get_channel(int(mapping.discord_channel_id)) is None:
                        channels.delete(mapping)
                        removed += 1
        return removed

    def status(self, guild_id: int, latency_seconds: float) -> AdministrationStatus:
        """Collect database, project, thread, and Gateway status."""
        with session_scope(self._session_factory) as session:
            session.execute(text("SELECT 1"))
            project_count = len(ProjectRepository(session).list_managed(guild_id))
            open_reviews = len(ReviewThreadRepository(session).list_open())
        return AdministrationStatus(
            project_count=project_count,
            open_review_count=open_reviews,
            latency_ms=max(0, round(latency_seconds * 1000)),
            database_ok=True,
        )

    def set_notifications(
        self, guild_id: int, project_name: str, enabled: bool
    ) -> None:
        """Enable or disable all notifications for a managed project."""
        with session_scope(self._session_factory) as session:
            projects = ProjectRepository(session)
            project = projects.find_managed(project_name.strip(), guild_id)
            if project is None:
                raise InvalidConfigurationError("프로젝트를 찾을 수 없습니다.")
            projects.update(project, enabled=enabled)

    def set_archive_days(self, days: int) -> None:
        """Set Discord-supported automatic archive duration."""
        if days not in {1, 3, 7}:
            raise ValueError("보관 기간은 1일, 3일 또는 7일이어야 합니다.")
        with session_scope(self._session_factory) as session:
            SettingRepository(session).set("archive_days", str(days))

    def set_auto_thread(self, enabled: bool) -> None:
        """Enable or disable automatic review thread creation."""
        with session_scope(self._session_factory) as session:
            SettingRepository(session).set(
                "auto_thread", "true" if enabled else "false"
            )

    def configure_reviewer(
        self,
        guild_id: int,
        project_name: str,
        action: str,
        user: discord.Member | None,
    ) -> list[str]:
        """Add, remove, or list project reviewers."""
        normalized_action = action.strip().lower()
        with session_scope(self._session_factory) as session:
            project = ProjectRepository(session).find_managed(
                project_name.strip(), guild_id
            )
            if project is None:
                raise InvalidConfigurationError("프로젝트를 찾을 수 없습니다.")
            reviewers = ReviewerRepository(session)
            if normalized_action == "list":
                return [
                    mapping.discord_user_id
                    for mapping in reviewers.list_for_project(project.id)
                ]
            if user is None:
                raise ValueError("추가하거나 삭제할 사용자를 선택해 주세요.")
            if normalized_action == "add":
                reviewers.add(project.id, user.id, user.display_name)
            elif normalized_action == "remove":
                reviewers.remove(project.id, user.id)
            else:
                raise ValueError("지원하지 않는 리뷰어 작업입니다.")
            return []
