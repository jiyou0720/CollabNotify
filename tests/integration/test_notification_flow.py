"""End-to-end service tests from webhook dispatch to Discord audit log."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import discord
import pytest
from sqlalchemy.orm import Session

from app.api.dependencies import get_event_dispatcher
from app.core.enums import ServiceType
from app.core.exceptions import DiscordApiError
from app.models.project import Project
from app.repositories.channel_repository import ChannelRepository
from app.repositories.error_repository import ErrorRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.project_alias_repository import ProjectAliasRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.review_thread_repository import ReviewThreadRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.common import Notification, NotificationField
from app.services.discord_service import DiscordService
from app.services.webhook_service import NotificationCoordinator, WebhookService
from database.session import create_session_factory


def seed_mapping(
    session: Session, service: str, project_name: str, channel_id: str
) -> Project:
    """Seed one alias and channel for a shared internal Discord project."""
    projects = ProjectRepository(session)
    project = projects.find_managed("Internal Project", 1)
    if project is None:
        project = projects.create(
            "Internal Project",
            "discord",
            "discord:1:internal-project",
            discord_guild_id="1",
            discord_category_id="10",
        )
    ChannelRepository(session).set_channel(service, project.id, channel_id)
    ProjectAliasRepository(session).create_alias(project.id, service, project_name)
    session.commit()
    return project


@pytest.mark.asyncio
async def test_all_services_reach_discord_and_audit_log(
    db_session: Session,
) -> None:
    """GitHub, Jira, and Confluence must complete the notification flow."""
    seed_mapping(db_session, "github", "org/repo", "101")
    seed_mapping(db_session, "jira", "CollabNotify", "102")
    seed_mapping(db_session, "confluence", "Development", "103")
    factory = create_session_factory(db_session.get_bind())
    message = Mock(spec=discord.Message)
    message.id = 900
    discord_service = Mock(spec=DiscordService)
    discord_service.send_embed = AsyncMock(return_value=message)
    coordinator = NotificationCoordinator(factory, discord_service)
    get_event_dispatcher.cache_clear()
    service = WebhookService(get_event_dispatcher(), coordinator)

    github = await service.process(
        ServiceType.GITHUB,
        "issues",
        {
            "action": "opened",
            "repository": {"full_name": "org/repo"},
            "issue": {
                "number": 1,
                "title": "Issue",
                "user": {"login": "author"},
                "html_url": "https://github.example/issues/1",
            },
        },
        "github-1",
    )
    jira = await service.process(
        ServiceType.JIRA,
        "jira:issue_created",
        {
            "issue": {
                "key": "CN-1",
                "fields": {
                    "summary": "Issue",
                    "project": {"name": "CollabNotify"},
                },
            }
        },
        "jira-1",
    )
    confluence = await service.process(
        ServiceType.CONFLUENCE,
        "page_created",
        {
            "page": {"title": "Page"},
            "space": {"name": "Development"},
            "user": {"displayName": "Author"},
        },
        "confluence-1",
    )

    assert github.supported and jira.supported and confluence.supported
    assert discord_service.send_embed.await_count == 3
    with factory() as verification_session:
        logs = NotificationRepository(verification_session).find_recent(
            datetime.now(UTC) - timedelta(minutes=1)
        )
    assert len(logs) == 3
    assert {log.status for log in logs} == {"SUCCESS"}
    assert len({log.project_id for log in logs}) == 1


@pytest.mark.asyncio
async def test_duplicate_delivery_is_idempotent(db_session: Session) -> None:
    """The same external event ID must not send twice."""
    seed_mapping(db_session, "github", "org/repo", "101")
    factory = create_session_factory(db_session.get_bind())
    message = Mock(spec=discord.Message)
    message.id = 901
    discord_service = Mock(spec=DiscordService)
    discord_service.send_embed = AsyncMock(return_value=message)
    get_event_dispatcher.cache_clear()
    service = WebhookService(
        get_event_dispatcher(), NotificationCoordinator(factory, discord_service)
    )
    payload = {
        "action": "opened",
        "repository": {"full_name": "org/repo"},
        "issue": {"number": 1, "title": "Issue"},
    }

    first = await service.process(ServiceType.GITHUB, "issues", payload, "delivery-1")
    second = await service.process(ServiceType.GITHUB, "issues", payload, "delivery-1")

    assert first.duplicate is False
    assert second.duplicate is True
    discord_service.send_embed.assert_awaited_once()


@pytest.mark.asyncio
async def test_jira_comment_appends_to_existing_issue_thread(
    db_session: Session,
) -> None:
    """Jira comments must retain project routing and mapped user mentions."""
    project = seed_mapping(db_session, "jira", "CollabNotify", "102")
    ReviewThreadRepository(db_session).create(
        project_id=project.id,
        service="jira",
        event_type="jira:issue_created",
        external_resource_id="CN-1",
        discord_message_id="901",
        discord_thread_id="902",
        title="CN-1 토론",
    )
    db_session.commit()
    factory = create_session_factory(db_session.get_bind())
    message = Mock(spec=discord.Message)
    message.id = 902
    discord_service = Mock(spec=DiscordService)
    discord_service.send_embed = AsyncMock(return_value=message)
    thread = Mock(spec=discord.Thread)
    thread.id = 902
    discord_service.get_thread.return_value = thread
    discord_service.send_thread_message = AsyncMock()
    discord_service.create_thread = AsyncMock()
    get_event_dispatcher.cache_clear()
    service = WebhookService(
        get_event_dispatcher(), NotificationCoordinator(factory, discord_service)
    )

    result = await service.process(
        ServiceType.JIRA,
        "comment_created",
        {
            "issueKey": "CN-1",
            "projectName": "CollabNotify",
            "issueUrl": "https://jira.example/browse/CN-1",
            "commentAuthor": "alice",
            "commentBody": "hello",
        },
        "jira-comment-1",
    )

    assert result.supported
    discord_service.send_embed.assert_not_awaited()
    discord_service.create_thread.assert_not_awaited()
    content = discord_service.send_thread_message.await_args.args[1]
    assert "💬 새 댓글" in content
    assert "alice" in content
    assert "hello" in content


@pytest.mark.asyncio
async def test_delivery_failure_persists_failed_notification_and_error(
    db_session: Session,
) -> None:
    """Permanent Discord failures must remain available for operations."""
    seed_mapping(db_session, "github", "org/repo", "101")
    factory = create_session_factory(db_session.get_bind())
    discord_service = Mock(spec=DiscordService)
    discord_service.send_embed = AsyncMock(side_effect=PermissionError("forbidden"))
    get_event_dispatcher.cache_clear()
    service = WebhookService(
        get_event_dispatcher(), NotificationCoordinator(factory, discord_service)
    )
    payload = {
        "action": "opened",
        "repository": {"full_name": "org/repo"},
        "issue": {"number": 1, "title": "Issue"},
    }

    with pytest.raises(DiscordApiError):
        await service.process(ServiceType.GITHUB, "issues", payload, "failed-1")

    with factory() as verification_session:
        failed = NotificationRepository(verification_session).find_failed()
        errors = ErrorRepository(verification_session).find_all()
    assert len(failed) == 1
    assert failed[0].external_event_id == "failed-1"
    assert errors[0].error_code == "GH005"


@pytest.mark.asyncio
async def test_notification_resolves_configured_role_mention(
    db_session: Session,
) -> None:
    """An explicit notification role must resolve to a safe Discord mention."""
    project = seed_mapping(db_session, "github", "org/repo", "101")
    RoleRepository(db_session).create(project.id, "Backend", "888")
    db_session.commit()
    factory = create_session_factory(db_session.get_bind())
    message = Mock(spec=discord.Message)
    message.id = 903
    discord_service = Mock(spec=DiscordService)
    discord_service.send_embed = AsyncMock(return_value=message)
    coordinator = NotificationCoordinator(factory, discord_service)
    notification = Notification(
        service=ServiceType.GITHUB,
        event_type="issues",
        title="Issue Opened",
        description="Issue",
        fields=(
            NotificationField(name="Repository", value="org/repo"),
            NotificationField(name="Role", value="Backend"),
        ),
    )

    assert await coordinator.deliver(notification, "role-mention-1")
    assert discord_service.send_embed.await_args.args[3] == "<@&888>"


@pytest.mark.asyncio
async def test_missing_alias_is_logged_and_safely_ignored(
    db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    """An unknown provider identifier must not raise or send a message."""
    discord_service = Mock(spec=DiscordService)
    discord_service.send_embed = AsyncMock()
    coordinator = NotificationCoordinator(
        create_session_factory(db_session.get_bind()), discord_service
    )
    notification = Notification(
        service=ServiceType.JIRA,
        event_type="jira:issue_created",
        title="이슈 생성",
        description="검토가 필요합니다.",
        fields=(NotificationField(name="프로젝트", value="CollabNotify"),),
    )

    assert await coordinator.deliver(notification, "jira-unmapped-1")

    discord_service.send_embed.assert_not_awaited()
    assert "Project alias not configured" in caplog.text
    assert "external_name=CollabNotify" in caplog.text


@pytest.mark.asyncio
async def test_jira_update_appends_once_to_existing_review_thread(
    db_session: Session,
) -> None:
    """A duplicate Jira update appends once and never creates another thread."""
    project = seed_mapping(db_session, "jira", "CollabNotify", "102")
    ReviewThreadRepository(db_session).create(
        project_id=project.id,
        service="jira",
        event_type="jira:issue_created",
        external_resource_id="CN-1",
        discord_message_id="900",
        discord_thread_id="901",
        title="CN-1 토론",
    )
    db_session.commit()
    message = Mock(spec=discord.Message)
    message.id = 902
    thread = Mock(spec=discord.Thread)
    thread.id = 901
    discord_service = Mock(spec=DiscordService)
    discord_service.send_embed = AsyncMock(return_value=message)
    discord_service.get_thread.return_value = thread
    discord_service.send_thread_message = AsyncMock()
    discord_service.set_thread_archived = AsyncMock()
    discord_service.create_thread = AsyncMock()
    factory = create_session_factory(db_session.get_bind())
    get_event_dispatcher.cache_clear()
    service = WebhookService(
        get_event_dispatcher(), NotificationCoordinator(factory, discord_service)
    )
    payload = {
        "webhookEvent": "jira:issue_updated",
        "user": {"displayName": "홍길동"},
        "issue": {
            "key": "CN-1",
            "fields": {"project": {"name": "CollabNotify"}},
        },
        "changelog": {
            "items": [
                {
                    "field": "priority",
                    "fromString": "Medium",
                    "toString": "High",
                }
            ]
        },
    }

    first = await service.process(
        ServiceType.JIRA, "jira:issue_updated", payload, "jira-update-1"
    )
    duplicate = await service.process(
        ServiceType.JIRA, "jira:issue_updated", payload, "jira-update-1"
    )

    assert first.duplicate is False
    assert duplicate.duplicate is True
    discord_service.create_thread.assert_not_awaited()
    discord_service.send_thread_message.assert_awaited_once()
    assert "⚠️ 우선순위 변경" in discord_service.send_thread_message.await_args.args[1]
    discord_service.edit_channel_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_github_pr_uses_one_thread_for_open_push_merge_and_duplicate(
    db_session: Session,
) -> None:
    """PR lifecycle keeps one thread and only parent-delivers open and merge."""
    seed_mapping(db_session, "github", "org/repo", "101")
    factory = create_session_factory(db_session.get_bind())
    parent_message = Mock(spec=discord.Message)
    parent_message.id = 500
    thread = Mock(spec=discord.Thread)
    thread.id = 600
    discord_service = Mock(spec=DiscordService)
    discord_service.send_embed = AsyncMock(return_value=parent_message)
    discord_service.create_thread = AsyncMock(return_value=thread)
    discord_service.edit_channel_message = AsyncMock(return_value=parent_message)
    discord_service.get_thread.return_value = thread
    discord_service.send_thread_message = AsyncMock()
    discord_service.set_thread_archived = AsyncMock()
    get_event_dispatcher.cache_clear()
    service = WebhookService(
        get_event_dispatcher(), NotificationCoordinator(factory, discord_service)
    )
    base_pr = {
        "number": 123,
        "title": "Improve login",
        "user": {"login": "author"},
        "base": {"ref": "main"},
        "head": {"ref": "feature"},
        "merged": False,
    }

    opened = await service.process(
        ServiceType.GITHUB,
        "pull_request",
        {
            "action": "opened",
            "repository": {"full_name": "org/repo"},
            "sender": {"login": "author"},
            "pull_request": base_pr,
        },
        "github-open-123",
    )
    push_payload = {
        "action": "synchronize",
        "repository": {"full_name": "org/repo"},
        "sender": {"login": "author"},
        "before": "a" * 40,
        "after": "b" * 40,
        "pull_request": {**base_pr, "commits": 1},
        "commits": [
            {
                "id": "b" * 40,
                "author": {"name": "author"},
                "message": "Fix login",
            }
        ],
    }
    pushed = await service.process(
        ServiceType.GITHUB,
        "pull_request",
        push_payload,
        "github-push-123",
    )
    duplicate = await service.process(
        ServiceType.GITHUB,
        "pull_request",
        push_payload,
        "github-push-123",
    )
    merged_pr = {**base_pr, "merged": True}
    merged = await service.process(
        ServiceType.GITHUB,
        "pull_request",
        {
            "action": "closed",
            "repository": {"full_name": "org/repo"},
            "sender": {"login": "merger"},
            "pull_request": merged_pr,
        },
        "github-merge-123",
    )

    assert opened.supported and pushed.supported and merged.supported
    assert duplicate.duplicate is True
    assert discord_service.send_embed.await_count == 1
    discord_service.create_thread.assert_awaited_once_with(
        parent_message, "🧵 PR #123 리뷰", 1440
    )
    assert discord_service.edit_channel_message.await_count == 2
    timeline_messages = [
        call.args[1] for call in discord_service.send_thread_message.await_args_list
    ]
    push_messages = [
        item for item in timeline_messages if "📦 새로운 코드가 Push되었습니다." in item
    ]
    assert len(push_messages) == 1
    discord_service.set_thread_archived.assert_awaited_once_with(
        600, archived=True, reason="CollabNotify GitHub PR 완료"
    )
    with factory() as session:
        reviews = ReviewThreadRepository(session)
        review = reviews.find_by_resource("github", "org/repo:pr:123")
        assert review is not None
        assert review.discord_thread_id == "600"
        assert review.status == "COMPLETED"


@pytest.mark.asyncio
async def test_confluence_page_uses_one_parent_embed_and_thread(
    db_session: Session,
) -> None:
    """Page updates, comments, and attachments reuse one parent and thread."""
    seed_mapping(db_session, "confluence", "Development", "103")
    factory = create_session_factory(db_session.get_bind())
    parent_message = Mock(spec=discord.Message)
    parent_message.id = 700
    thread = Mock(spec=discord.Thread)
    thread.id = 701
    discord_service = Mock(spec=DiscordService)
    discord_service.send_embed = AsyncMock(return_value=parent_message)
    discord_service.create_thread = AsyncMock(return_value=thread)
    discord_service.get_thread.return_value = thread
    discord_service.send_thread_message = AsyncMock()
    discord_service.edit_channel_message = AsyncMock(return_value=parent_message)
    discord_service.set_thread_archived = AsyncMock()
    get_event_dispatcher.cache_clear()
    service = WebhookService(
        get_event_dispatcher(), NotificationCoordinator(factory, discord_service)
    )
    base = {
        "page": {"id": "10", "title": "Architecture"},
        "space": {"name": "Development"},
        "user": {"displayName": "Editor"},
    }

    await service.process(ServiceType.CONFLUENCE, "page_created", base, "cf-created-10")
    await service.process(
        ServiceType.CONFLUENCE,
        "page_updated",
        {
            **base,
            "page": {
                "id": "10",
                "title": "Architecture",
                "version": {"number": 2},
            },
        },
        "cf-updated-10",
    )
    await service.process(
        ServiceType.CONFLUENCE,
        "comment_created",
        {**base, "comment": {"body": "검토 의견"}},
        "cf-comment-10",
    )
    await service.process(
        ServiceType.CONFLUENCE,
        "attachment_created",
        {**base, "attachment": {"title": "diagram.png", "fileSize": 2048}},
        "cf-attachment-10",
    )
    await service.process(
        ServiceType.CONFLUENCE,
        "page_deleted",
        base,
        "cf-deleted-10",
    )

    discord_service.send_embed.assert_awaited_once()
    discord_service.create_thread.assert_awaited_once()
    discord_service.edit_channel_message.assert_awaited_once()
    messages = [
        call.args[1] for call in discord_service.send_thread_message.await_args_list
    ]
    assert any("📝 문서 수정" in item for item in messages)
    assert all("버전 변경" not in item for item in messages)
    assert any("💬 새 댓글" in item for item in messages)
    assert any("📎 첨부파일 추가" in item for item in messages)
    assert any("문서가 삭제되었습니다." in item for item in messages)
    discord_service.set_thread_archived.assert_awaited_once_with(
        701,
        archived=True,
        reason="CollabNotify Confluence 문서 삭제",
    )
    with factory() as session:
        review = ReviewThreadRepository(session).find_by_resource("confluence", "10")
        assert review is not None
        assert review.discord_thread_id == "701"
        assert review.status == "COMPLETED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("event_type", "payload"),
    [
        (
            "page_updated",
            {
                "page": {
                    "id": "legacy-10",
                    "title": "Legacy Architecture",
                    "version": {"number": 2},
                },
                "space": {"name": "Development"},
                "user": {"displayName": "Editor"},
            },
        ),
        (
            "comment_created",
            {
                "page": {"id": "legacy-10", "title": "Legacy Architecture"},
                "comment": {"body": "첫 번째로 감지된 댓글"},
                "space": {"name": "Development"},
                "user": {"displayName": "Reviewer"},
            },
        ),
    ],
)
async def test_first_legacy_page_activity_creates_parent_card_and_linked_thread(
    db_session: Session,
    event_type: str,
    payload: dict[str, object],
) -> None:
    """A first update or comment must not create an orphan standalone thread."""
    seed_mapping(db_session, "confluence", "Development", "103")
    factory = create_session_factory(db_session.get_bind())
    parent_message = Mock(spec=discord.Message)
    parent_message.id = 800
    controls_message = Mock(spec=discord.Message)
    controls_message.id = 802
    thread = Mock(spec=discord.Thread)
    thread.id = 801
    discord_service = Mock(spec=DiscordService)
    discord_service.send_embed = AsyncMock(return_value=parent_message)
    discord_service.create_thread = AsyncMock(return_value=thread)
    discord_service.create_channel_thread = AsyncMock()
    discord_service.send_thread_controls = AsyncMock(return_value=controls_message)
    discord_service.send_thread_message = AsyncMock()
    discord_service.get_thread.return_value = thread
    get_event_dispatcher.cache_clear()
    service = WebhookService(
        get_event_dispatcher(), NotificationCoordinator(factory, discord_service)
    )

    result = await service.process(
        ServiceType.CONFLUENCE,
        event_type,
        payload,
        f"cf-{event_type}-legacy-10",
    )

    assert result.supported is True
    discord_service.send_embed.assert_awaited_once()
    discord_service.create_thread.assert_awaited_once()
    assert discord_service.create_thread.await_args.args[0] is parent_message
    discord_service.create_channel_thread.assert_not_awaited()
    with factory() as session:
        review = ReviewThreadRepository(session).find_by_resource(
            "confluence", "legacy-10"
        )
        assert review is not None
        assert review.discord_message_id == "800"
        assert review.discord_thread_id == "801"
