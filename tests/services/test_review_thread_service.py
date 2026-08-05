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
from app.schemas.common import Notification, NotificationActivity, NotificationField
from app.services.discord_service import DiscordService
from app.services.review_thread_service import REVIEW_CHECKLIST, ReviewThreadService
from app.services.thread_manager import ThreadManager
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


def confluence_update_notification() -> Notification:
    """Create a Confluence page update without an existing thread mapping."""
    return Notification(
        service=ServiceType.CONFLUENCE,
        event_type="page_updated",
        title="문서 수정",
        description="Architecture",
        fields=(NotificationField(name="스페이스", value="Development"),),
        external_resource_id="12189697",
        review_action="APPEND",
        review_thread_title="🧵 Architecture 리뷰",
        activities=(
            NotificationActivity(
                kind="confluence_page_updated",
                actor="jiyou",
                occurred_at="2026-08-03T13:33:30Z",
                body="Architecture",
            ),
        ),
        parent_delivery=False,
        parent_update=True,
    )


def jira_timeline_service(
    session: Session, *, completed: bool = False
) -> tuple[ReviewThreadService, Mock, Mock]:
    """Create a Jira review mapping and mocked Discord thread operations."""
    project = ProjectRepository(session).create("Internal", "discord")
    review = ReviewThreadRepository(session).create(
        project_id=project.id,
        service="jira",
        event_type="jira:issue_created",
        external_resource_id="CN-1",
        discord_message_id="200",
        discord_thread_id="300",
        title="CN-1 토론",
    )
    if completed:
        ReviewThreadRepository(session).update_status(review, "COMPLETED")
    session.commit()
    thread = Mock(spec=discord.Thread)
    thread.id = 300
    discord_service = Mock(spec=DiscordService)
    discord_service.get_thread.return_value = thread
    discord_service.send_thread_message = AsyncMock()
    discord_service.set_thread_archived = AsyncMock()
    service = ReviewThreadService(
        create_session_factory(session.get_bind()), discord_service
    )
    return service, discord_service, thread


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
    assert isinstance(service, ThreadManager)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ("github", "jira", "confluence"))
async def test_common_thread_manager_finds_and_posts_for_every_provider(
    db_session: Session, provider: str
) -> None:
    """All providers use the same persisted lookup and posting interface."""
    project = ProjectRepository(db_session).create(f"{provider}-project", "discord")
    ReviewThreadRepository(db_session).create(
        project_id=project.id,
        service=provider,
        event_type="created",
        external_resource_id="object-1",
        discord_message_id="200",
        discord_thread_id="300",
        title="공통 리뷰",
    )
    db_session.commit()
    thread = Mock(spec=discord.Thread)
    thread.id = 300
    discord_service = Mock(spec=DiscordService)
    discord_service.get_thread.return_value = thread
    discord_service.send_thread_message = AsyncMock()
    service = ReviewThreadService(
        create_session_factory(db_session.get_bind()), discord_service
    )

    mapping = service.find_thread(provider, "object-1")
    posted = await service.post_to_thread(provider, "object-1", "활동 기록")

    assert mapping is not None
    assert mapping.discord_thread_id == "300"
    assert posted is True
    discord_service.send_thread_message.assert_awaited_once_with(thread, "활동 기록")


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "title"),
    (
        ("status", "🔄 상태 변경"),
        ("assignee", "👤 담당자 변경"),
        ("priority", "⚠️ 우선순위 변경"),
    ),
)
async def test_jira_changes_append_separate_korean_messages(
    db_session: Session, kind: str, title: str
) -> None:
    """Tracked Jira changes are posted through DiscordService."""
    service, discord_service, thread = jira_timeline_service(db_session)
    activity = NotificationActivity(
        kind=kind, before="이전", after="이후", actor="홍길동"
    )

    assert await service.append_activities("jira", "CN-1", (activity,))

    content = discord_service.send_thread_message.await_args.args[1]
    assert discord_service.send_thread_message.await_args.args[0] is thread
    assert title in content
    assert "이전\n→\n이후" in content
    assert "홍길동" in content


@pytest.mark.asyncio
async def test_jira_comment_appends_to_existing_thread(db_session: Session) -> None:
    """A Jira comment is added to the mapped issue thread."""
    service, discord_service, _thread = jira_timeline_service(db_session)
    activity = NotificationActivity(
        kind="comment_created", actor="홍길동", body="댓글 내용"
    )

    await service.append_activities("jira", "CN-1", (activity,))

    content = discord_service.send_thread_message.await_args.args[1]
    assert "💬 새 댓글" in content
    assert "홍길동" in content
    assert "댓글 내용" in content


@pytest.mark.asyncio
async def test_done_status_archives_jira_thread(db_session: Session) -> None:
    """A transition to Done posts completion and archives the thread."""
    service, discord_service, _thread = jira_timeline_service(db_session)

    await service.append_activities(
        "jira",
        "CN-1",
        (NotificationActivity(kind="status", before="진행 중", after="Done"),),
    )

    discord_service.set_thread_archived.assert_awaited_once_with(
        300, archived=True, reason="CollabNotify Jira 작업 완료"
    )
    messages = [
        call.args[1] for call in discord_service.send_thread_message.await_args_list
    ]
    assert "✅ 작업이 완료되었습니다." in messages
    assert service.get_status(300).status == "COMPLETED"


@pytest.mark.asyncio
async def test_all_update_messages_are_sent_before_archive(
    db_session: Session,
) -> None:
    """A multi-field Done update cannot archive before later activities."""
    service, discord_service, _thread = jira_timeline_service(db_session)
    operations: list[str] = []
    discord_service.send_thread_message.side_effect = lambda *_args, **_kwargs: (
        operations.append("message")
    )
    discord_service.set_thread_archived.side_effect = lambda *_args, **_kwargs: (
        operations.append("archive")
    )

    await service.append_activities(
        "jira",
        "CN-1",
        (
            NotificationActivity(kind="status", before="진행 중", after="Done"),
            NotificationActivity(kind="priority", before="Medium", after="High"),
        ),
    )

    assert operations == ["message", "message", "message", "archive"]


@pytest.mark.asyncio
async def test_reopened_status_unarchives_jira_thread(db_session: Session) -> None:
    """A Done-to-active transition reopens the same thread."""
    service, discord_service, _thread = jira_timeline_service(
        db_session, completed=True
    )

    await service.append_activities(
        "jira",
        "CN-1",
        (NotificationActivity(kind="status", before="Done", after="진행 중"),),
    )

    discord_service.set_thread_archived.assert_awaited_once_with(
        300, archived=False, reason="CollabNotify Jira 작업 재개"
    )
    messages = [
        call.args[1] for call in discord_service.send_thread_message.await_args_list
    ]
    assert "♻️ 작업이 다시 진행됩니다." in messages
    assert service.get_status(300).status == "IN_REVIEW"


@pytest.mark.asyncio
async def test_missing_jira_thread_logs_and_does_not_create(
    db_session: Session,
) -> None:
    """Timeline activity without a mapping is safely ignored."""
    discord_service = Mock(spec=DiscordService)
    discord_service.create_thread = AsyncMock()
    discord_service.send_thread_message = AsyncMock()
    service = ReviewThreadService(
        create_session_factory(db_session.get_bind()), discord_service
    )
    service._logger = Mock()

    result = await service.append_activities(
        "jira",
        "CN-404",
        (NotificationActivity(kind="status", before="To Do", after="Done"),),
    )

    assert result is False
    service._logger.warning.assert_called_once_with(
        "Review thread missing: service=%s resource=%s", "jira", "CN-404"
    )
    discord_service.create_thread.assert_not_awaited()
    discord_service.send_thread_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_confluence_update_creates_thread(
    db_session: Session,
) -> None:
    """A legacy Confluence page update bootstraps its own review thread."""
    project = ProjectRepository(db_session).create("Internal", "discord")
    db_session.commit()
    factory = create_session_factory(db_session.get_bind())
    thread = Mock(spec=discord.Thread)
    thread.id = 700
    discord_service = Mock(spec=DiscordService)
    discord_service.create_channel_thread = AsyncMock(return_value=thread)
    discord_service.send_thread_message = AsyncMock()
    controls_message = Mock(spec=discord.Message)
    controls_message.id = 701
    discord_service.send_thread_controls = AsyncMock(return_value=controls_message)
    service = ReviewThreadService(factory, discord_service)

    review = await service.process_notification(
        confluence_update_notification(),
        project.id,
        message=None,
        channel_id=103,
    )

    assert review is not None
    assert review.external_resource_id == "12189697"
    discord_service.create_channel_thread.assert_awaited_once_with(
        103, "🧵 Architecture 리뷰", 1440
    )
    messages = [
        call.args[1] for call in discord_service.send_thread_message.await_args_list
    ]
    discord_service.send_thread_controls.assert_awaited_once()
    controls_content = discord_service.send_thread_controls.await_args.args[1]
    assert "문서 리뷰" in controls_content
    assert "기준 설정 필요" in controls_content
    assert REVIEW_CHECKLIST not in messages
    assert any("📝 문서 수정" in message for message in messages)
    assert all("버전 변경" not in message for message in messages)
