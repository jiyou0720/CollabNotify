"""Tests for automatic review thread lifecycle."""

from unittest.mock import AsyncMock, Mock

import discord
import pytest
from sqlalchemy.orm import Session

from app.core.enums import ServiceType
from app.core.exceptions import InvalidConfigurationError
from app.repositories.project_repository import ProjectRepository
from app.repositories.review_thread_repository import ReviewThreadRepository
from app.repositories.setting_repository import SettingRepository
from app.schemas.common import Notification, NotificationField
from app.services.discord_service import DiscordService
from app.services.review_thread_service import REVIEW_CHECKLIST, ReviewThreadService
from database.session import create_session_factory


def review_notification(action: str = "OPEN") -> Notification:
    """Create a normalized GitHub review event."""
    return Notification(
        service=ServiceType.GITHUB,
        event_type="pull_request",
        title="PR 생성",
        description="리뷰가 필요합니다.",
        fields=(NotificationField(name="저장소", value="org/repo"),),
        external_resource_id="org/repo:pr:42",
        review_action=action,
        review_thread_title="🧵 PR #42 리뷰",
    )


@pytest.mark.asyncio
async def test_open_event_creates_thread_and_checklist(db_session: Session) -> None:
    """Important events must create one persisted review discussion."""
    project = ProjectRepository(db_session).create("org/repo", "github")
    db_session.commit()
    factory = create_session_factory(db_session.get_bind())
    thread = Mock(spec=discord.Thread)
    thread.id = 300
    message = Mock(spec=discord.Message)
    message.id = 200
    discord_service = Mock(spec=DiscordService)
    discord_service.create_thread = AsyncMock(return_value=thread)
    discord_service.send_thread_message = AsyncMock()
    service = ReviewThreadService(factory, discord_service)

    review = await service.process_notification(
        review_notification(), project.id, message
    )

    assert review is not None
    assert review.status == "IN_REVIEW"
    discord_service.create_thread.assert_awaited_once_with(
        message, "🧵 PR #42 리뷰", 1440
    )
    discord_service.send_thread_message.assert_awaited_once_with(
        thread, REVIEW_CHECKLIST
    )


@pytest.mark.asyncio
async def test_close_event_archives_existing_review(db_session: Session) -> None:
    """Completion events must archive the corresponding review thread."""
    project = ProjectRepository(db_session).create("org/repo", "github")
    reviews = ReviewThreadRepository(db_session)
    review = reviews.create(
        project_id=project.id,
        service="github",
        event_type="pull_request",
        external_resource_id="org/repo:pr:42",
        discord_message_id="200",
        discord_thread_id="300",
        title="PR #42 리뷰",
    )
    db_session.commit()
    factory = create_session_factory(db_session.get_bind())
    discord_service = Mock(spec=DiscordService)
    discord_service.archive_thread = AsyncMock()
    service = ReviewThreadService(factory, discord_service)
    message = Mock(spec=discord.Message)
    message.id = 201

    await service.process_notification(
        review_notification("CLOSE"), project.id, message
    )

    discord_service.archive_thread.assert_awaited_once_with(300)
    with factory() as session:
        persisted = ReviewThreadRepository(session).find_by_resource(
            "github", "org/repo:pr:42"
        )
        assert persisted is not None
        assert persisted.status == "COMPLETED"
    assert review.id == persisted.id


@pytest.mark.asyncio
async def test_auto_thread_setting_disables_creation(db_session: Session) -> None:
    """Administrators must be able to disable automatic thread creation."""
    project = ProjectRepository(db_session).create("org/repo", "github")
    SettingRepository(db_session).set("auto_thread", "false")
    db_session.commit()
    factory = create_session_factory(db_session.get_bind())
    discord_service = Mock(spec=DiscordService)
    discord_service.create_thread = AsyncMock()
    service = ReviewThreadService(factory, discord_service)

    result = await service.process_notification(
        review_notification(), project.id, Mock(spec=discord.Message)
    )

    assert result is None
    discord_service.create_thread.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_thread_is_not_modified(db_session: Session) -> None:
    """A review command must never mutate an unregistered Discord thread."""
    factory = create_session_factory(db_session.get_bind())
    discord_service = Mock(spec=DiscordService)
    discord_service.archive_thread = AsyncMock()
    discord_service.send_thread_message = AsyncMock()
    service = ReviewThreadService(factory, discord_service)

    with pytest.raises(InvalidConfigurationError):
        await service.update_status(999, "COMPLETED", 100)

    discord_service.archive_thread.assert_not_awaited()
    discord_service.send_thread_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_completed_status_is_idempotent_and_terminal(
    db_session: Session,
) -> None:
    """Completion must be idempotent and prevent reopening archived reviews."""
    project = ProjectRepository(db_session).create("org/repo", "github")
    review = ReviewThreadRepository(db_session).create(
        project_id=project.id,
        service="github",
        event_type="pull_request",
        external_resource_id="org/repo:pr:42",
        discord_message_id="200",
        discord_thread_id="300",
        title="PR #42 리뷰",
    )
    ReviewThreadRepository(db_session).update_status(review, "COMPLETED")
    db_session.commit()
    discord_service = Mock(spec=DiscordService)
    discord_service.archive_thread = AsyncMock()
    discord_service.send_thread_message = AsyncMock()
    service = ReviewThreadService(
        create_session_factory(db_session.get_bind()), discord_service
    )

    unchanged = await service.update_status(300, "COMPLETED", 100)
    with pytest.raises(InvalidConfigurationError):
        await service.update_status(300, "APPROVED", 100)

    assert unchanged.status == "COMPLETED"
    discord_service.archive_thread.assert_not_awaited()
    discord_service.send_thread_message.assert_not_awaited()
