"""CRUD and integrity tests for SQLAlchemy Repositories."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.channel_repository import ChannelRepository
from app.repositories.error_repository import ErrorRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.setting_repository import SettingRepository
from app.repositories.user_repository import UserRepository


def test_project_and_mapping_crud(db_session: Session) -> None:
    """Project, channel, user, and role mappings must support CRUD."""
    projects = ProjectRepository(db_session)
    project = projects.create("CollabNotify", "github", "repo-1")
    channel = ChannelRepository(db_session).create("github", project.id, "100")
    user = UserRepository(db_session).save_mapping(
        "github", "developer", "200", "Developer"
    )
    role = RoleRepository(db_session).create(project.id, "Backend", "300")

    assert projects.find_by_id(project.id) is project
    assert projects.find_by_name("CollabNotify", "github") is project
    assert ChannelRepository(db_session).find_channel("github", project.id) is channel
    assert UserRepository(db_session).find_discord_user("github", "developer") is user
    assert RoleRepository(db_session).find_role(project.id, "Backend") is role

    projects.update(project, enabled=False)
    assert project.enabled is False


def test_project_delete_cascades_mappings(db_session: Session) -> None:
    """Deleting a Project must remove its channel and role mappings."""
    projects = ProjectRepository(db_session)
    project = projects.create("Project", "jira", "jira-1")
    channel = ChannelRepository(db_session).create("jira", project.id, "100")
    role = RoleRepository(db_session).create(project.id, "Team", "200")
    channel_id = channel.id
    role_id = role.id

    projects.delete(project)

    assert db_session.get(type(channel), channel_id) is None
    assert db_session.get(type(role), role_id) is None


def test_notification_log_status_and_idempotency(db_session: Session) -> None:
    """Notification logs must track status and prevent duplicate events."""
    repository = NotificationRepository(db_session)
    log = repository.create(
        service="github",
        event_type="issues",
        external_event_id="delivery-1",
        status="RETRY",
    )

    assert repository.exists("github", "delivery-1") is True
    repository.update_status(log, "SUCCESS", "message-1")
    assert log.status == "SUCCESS"
    assert log.discord_message_id == "message-1"

    with pytest.raises(IntegrityError):
        repository.create(
            service="github",
            event_type="issues",
            external_event_id="delivery-1",
            status="SUCCESS",
        )
    db_session.rollback()


def test_notification_queries(db_session: Session) -> None:
    """Recent and failed delivery queries must return matching logs."""
    repository = NotificationRepository(db_session)
    repository.create(service="jira", event_type="issue", status="FAILED")
    repository.create(service="jira", event_type="comment", status="SUCCESS")

    assert len(repository.find_failed()) == 1
    assert len(repository.find_recent(datetime.now(UTC) - timedelta(minutes=1))) == 2
    assert (
        len(
            repository.find_recent(
                datetime.now(UTC) - timedelta(minutes=1), limit=1, offset=1
            )
        )
        == 1
    )
    with pytest.raises(ValueError):
        repository.find_recent(datetime.now(UTC), limit=0)


def test_error_and_setting_repositories(db_session: Session) -> None:
    """Error and setting repositories must persist operational data."""
    errors = ErrorRepository(db_session)
    error = errors.save(error_code="SYS001", message="Failure", service="system")
    settings = SettingRepository(db_session)
    setting = settings.set("retry_count", "3")

    assert errors.find_all() == [error]
    assert settings.get("retry_count") is setting

    settings.set("retry_count", "4")
    assert setting.value == "4"
