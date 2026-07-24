"""End-to-end service tests from webhook dispatch to Discord audit log."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import discord
import pytest
from sqlalchemy.orm import Session

from app.api.dependencies import get_event_dispatcher
from app.core.enums import ServiceType
from app.core.exceptions import DiscordApiError, InvalidConfigurationError
from app.repositories.channel_repository import ChannelRepository
from app.repositories.error_repository import ErrorRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import Notification, NotificationField
from app.services.discord_service import DiscordService
from app.services.webhook_service import NotificationCoordinator, WebhookService
from database.session import create_session_factory


def seed_mapping(
    session: Session, service: str, project_name: str, channel_id: str
) -> None:
    """Seed one project and Discord channel mapping."""
    project = ProjectRepository(session).create(
        project_name, service, f"{service}-{project_name}"
    )
    ChannelRepository(session).create(service, project.id, channel_id)
    session.commit()


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
async def test_jira_comment_resolves_project_and_user_mention(
    db_session: Session,
) -> None:
    """Jira comments must retain project routing and mapped user mentions."""
    seed_mapping(db_session, "jira", "CollabNotify", "102")
    UserRepository(db_session).save_mapping("jira", "alice", "777")
    db_session.commit()
    factory = create_session_factory(db_session.get_bind())
    message = Mock(spec=discord.Message)
    message.id = 902
    discord_service = Mock(spec=DiscordService)
    discord_service.send_embed = AsyncMock(return_value=message)
    get_event_dispatcher.cache_clear()
    service = WebhookService(
        get_event_dispatcher(), NotificationCoordinator(factory, discord_service)
    )

    result = await service.process(
        ServiceType.JIRA,
        "comment_created",
        {
            "issue": {
                "key": "CN-1",
                "fields": {"project": {"name": "CollabNotify"}},
                "self": "https://jira.example/rest/api/issue/CN-1",
            },
            "comment": {"body": "hello", "author": {"displayName": "alice"}},
        },
        "jira-comment-1",
    )

    assert result.supported
    assert discord_service.send_embed.await_args.args[3] == "<@777>"


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
    seed_mapping(db_session, "github", "org/repo", "101")
    project = ProjectRepository(db_session).find_by_name("org/repo", "github")
    assert project is not None
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
async def test_managed_project_routing_rejects_cross_guild_ambiguity(
    db_session: Session,
) -> None:
    """A webhook must never choose arbitrarily between identically named guilds."""
    projects = ProjectRepository(db_session)
    for guild_id, channel_id in (("10", "101"), ("20", "102")):
        project = projects.create(
            "CollabNotify",
            "discord",
            f"discord:{guild_id}:collabnotify",
            discord_guild_id=guild_id,
            discord_category_id=f"{guild_id}0",
        )
        ChannelRepository(db_session).create("jira", project.id, channel_id, "jira")
    db_session.commit()
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

    with pytest.raises(InvalidConfigurationError):
        await coordinator.deliver(notification, "jira-ambiguous-1")

    discord_service.send_embed.assert_not_awaited()
