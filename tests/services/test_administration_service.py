"""Tests for Discord administration and persistent settings."""

from unittest.mock import Mock

import discord
from sqlalchemy.orm import Session

from app.repositories.channel_repository import ChannelRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.reviewer_repository import ReviewerRepository
from app.repositories.setting_repository import SettingRepository
from app.services.administration_service import AdministrationService
from database.session import create_session_factory


def seed_managed_project(session: Session) -> int:
    """Create one managed project and return its database ID."""
    project = ProjectRepository(session).create(
        "CampusFlow",
        "discord",
        "discord:10:campusflow",
        discord_guild_id="10",
        discord_category_id="20",
    )
    session.commit()
    return project.id


def test_administration_cleanup_and_status(db_session: Session) -> None:
    """Cleanup must remove stale mappings and status must query the database."""
    project_id = seed_managed_project(db_session)
    ChannelRepository(db_session).create("github", project_id, "30", "github")
    db_session.commit()
    guild = Mock(spec=discord.Guild)
    guild.id = 10
    guild.get_channel.return_value = None
    service = AdministrationService(create_session_factory(db_session.get_bind()))

    removed = service.cleanup(guild)
    status = service.status(10, 0.125)

    assert removed == 1
    assert status.project_count == 1
    assert status.open_review_count == 0
    assert status.latency_ms == 125
    assert status.database_ok is True


def test_administration_persists_settings_and_reviewers(
    db_session: Session,
) -> None:
    """Notification, archive, auto-thread, and reviewer settings must persist."""
    project_id = seed_managed_project(db_session)
    factory = create_session_factory(db_session.get_bind())
    service = AdministrationService(factory)
    member = Mock(spec=discord.Member)
    member.id = 100
    member.display_name = "리뷰어"

    service.set_notifications(10, "CampusFlow", False)
    service.set_archive_days(3)
    service.set_auto_thread(False)
    service.configure_reviewer(10, "CampusFlow", "add", member)
    service.configure_reviewer(10, "CampusFlow", "add", member)
    reviewer_ids = service.configure_reviewer(10, "CampusFlow", "list", None)

    with factory() as session:
        project = ProjectRepository(session).find_managed("CampusFlow", 10)
        assert project is not None
        assert project.enabled is False
        assert SettingRepository(session).get("archive_days").value == "3"
        assert SettingRepository(session).get("auto_thread").value == "false"
        assert ReviewerRepository(session).list_for_project(project_id)
    assert reviewer_ids == ["100"]
