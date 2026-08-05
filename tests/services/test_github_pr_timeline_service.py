"""GitHub pull-request timeline service tests."""

from unittest.mock import AsyncMock, Mock

import discord
import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ChannelNotFoundError
from app.repositories.project_repository import ProjectRepository
from app.repositories.review_thread_repository import ReviewThreadRepository
from app.schemas.common import NotificationActivity
from app.services.discord_service import DiscordService
from app.services.review_thread_service import ReviewThreadService
from database.session import create_session_factory


def github_timeline_service(
    session: Session, *, completed: bool = False
) -> tuple[ReviewThreadService, Mock]:
    """Create a mapped GitHub PR thread and mocked Discord boundary."""
    project = ProjectRepository(session).create("Internal", "discord")
    review = ReviewThreadRepository(session).create(
        project_id=project.id,
        service="github",
        event_type="pull_request",
        external_resource_id="org/repo:pr:123",
        discord_message_id="200",
        discord_thread_id="300",
        title="PR #123 리뷰",
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
    return (
        ReviewThreadService(
            create_session_factory(session.get_bind()), discord_service
        ),
        discord_service,
    )


@pytest.mark.asyncio
async def test_push_is_one_compact_thread_message(db_session: Session) -> None:
    """Multiple synchronize commits are summarized in one Discord message."""
    service, discord_service = github_timeline_service(db_session)
    activity = NotificationActivity(
        kind="github_push",
        actor="홍길동",
        after="abcdef1",
        body="`abcdef1` · 홍길동 · Fix login\n`1234567` · 김철수 · Add tests",
        added=("2",),
    )

    await service.append_activities("github", "org/repo:pr:123", (activity,))

    discord_service.send_thread_message.assert_awaited_once()
    content = discord_service.send_thread_message.await_args.args[1]
    assert "📦 새로운 코드가 Push되었습니다." in content
    assert "커밋 수: 2" in content
    assert "abcdef1" in content and "1234567" in content


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "title"),
    (("approved", "✅ 리뷰 승인"), ("changes_requested", "🔄 변경 요청")),
)
async def test_review_state_uses_korean_message(
    db_session: Session, state: str, title: str
) -> None:
    """Review approval and change requests use distinct Korean messages."""
    service, discord_service = github_timeline_service(db_session)

    await service.append_activities(
        "github",
        "org/repo:pr:123",
        (
            NotificationActivity(
                kind="github_review_submitted",
                after=state,
                actor="김철수",
            ),
        ),
    )

    content = discord_service.send_thread_message.await_args.args[1]
    assert title in content
    assert "김철수" in content


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "title"),
    (
        ("github_review_comment_created", "💬 리뷰 댓글"),
        ("github_issue_comment_created", "📝 댓글"),
    ),
)
async def test_github_comments_use_the_existing_thread(
    db_session: Session, kind: str, title: str
) -> None:
    """Review and issue comments are formatted without parent delivery."""
    service, discord_service = github_timeline_service(db_session)

    await service.append_activities(
        "github",
        "org/repo:pr:123",
        (NotificationActivity(kind=kind, actor="김철수", body="검토 의견"),),
    )

    content = discord_service.send_thread_message.await_args.args[1]
    assert title in content
    assert "김철수" in content
    assert "검토 의견" in content


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ("github_pr_merged", "github_pr_closed"))
async def test_completed_pr_archives_without_thread_completion_message(
    db_session: Session, kind: str
) -> None:
    """PR completion is appended before the existing thread is archived."""
    service, discord_service = github_timeline_service(db_session)

    await service.append_activities(
        "github",
        "org/repo:pr:123",
        (NotificationActivity(kind=kind, actor="홍길동"),),
    )

    content = discord_service.send_thread_message.await_args.args[1]
    expected = "✅ PR Merged" if kind == "github_pr_merged" else "🔒 PR Closed"
    assert content == expected
    discord_service.set_thread_archived.assert_awaited_once_with(
        300, archived=True, reason="CollabNotify GitHub PR 완료"
    )
    assert service.get_status(300).status == "COMPLETED"


@pytest.mark.asyncio
async def test_reopened_pr_unarchives_same_thread(db_session: Session) -> None:
    """Reopening restores the completed PR thread and posts a notice."""
    service, discord_service = github_timeline_service(db_session, completed=True)

    await service.append_activities(
        "github",
        "org/repo:pr:123",
        (NotificationActivity(kind="github_pr_reopened", actor="홍길동"),),
    )

    discord_service.set_thread_archived.assert_awaited_once_with(
        300, archived=False, reason="CollabNotify GitHub PR 재개"
    )
    assert (
        discord_service.send_thread_message.await_args.args[1]
        == "♻️ PR가 다시 열렸습니다."
    )
    assert service.get_status(300).status == "IN_REVIEW"


@pytest.mark.asyncio
async def test_reopened_pr_unarchives_auto_archived_active_thread(
    db_session: Session,
) -> None:
    """GitHub reopen also restores a thread archived by Discord inactivity."""
    service, discord_service = github_timeline_service(db_session)

    await service.append_activities(
        "github",
        "org/repo:pr:123",
        (NotificationActivity(kind="github_pr_reopened", actor="홍길동"),),
    )

    discord_service.set_thread_archived.assert_awaited_once_with(
        300, archived=False, reason="CollabNotify GitHub PR 재개"
    )
    assert service.get_status(300).status == "IN_REVIEW"


@pytest.mark.asyncio
async def test_parent_embed_is_updated_without_new_message(db_session: Session) -> None:
    """State changes edit the mapped parent message through DiscordService."""
    service, discord_service = github_timeline_service(db_session)
    discord_service.edit_channel_message = AsyncMock()
    embed = discord.Embed(title="최신 상태")

    updated = await service.update_parent_message(
        "github", "org/repo:pr:123", 100, embed
    )

    assert updated is True
    discord_service.edit_channel_message.assert_awaited_once_with(100, 200, embed, None)


@pytest.mark.asyncio
async def test_legacy_missing_parent_does_not_block_timeline(
    db_session: Session,
) -> None:
    """Legacy standalone-thread mappings tolerate an unavailable parent message."""
    service, discord_service = github_timeline_service(db_session)
    discord_service.edit_channel_message = AsyncMock(
        side_effect=ChannelNotFoundError("missing")
    )

    updated = await service.update_parent_message(
        "github", "org/repo:pr:123", 100, discord.Embed(title="상태")
    )

    assert updated is False
