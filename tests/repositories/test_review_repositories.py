"""Tests for Phase 13 and 14 persistence operations."""

from sqlalchemy.orm import Session

from app.repositories.channel_repository import ChannelRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.review_thread_repository import ReviewThreadRepository
from app.repositories.reviewer_repository import ReviewerRepository


def test_managed_project_and_default_channel_mappings(db_session: Session) -> None:
    """Managed projects must retain Discord category and channel metadata."""
    projects = ProjectRepository(db_session)
    project = projects.create(
        "CampusFlow",
        "discord",
        "discord:10:CampusFlow",
        discord_guild_id="10",
        discord_category_id="20",
    )
    channels = ChannelRepository(db_session)
    mapping = channels.set_channel("github", project.id, "30", "github")
    channels.set_channel("jira", project.id, "31", "jira")

    assert projects.find_managed("CampusFlow", 10) is project
    assert projects.list_managed(10) == [project]
    assert len(channels.list_for_project(project.id)) == 2
    channels.set_channel("github", project.id, "32", "github-updated")
    assert mapping.discord_channel_id == "32"
    assert channels.delete_service("jira", project.id) is True


def test_review_thread_status_and_reviewer_history(db_session: Session) -> None:
    """Review status transitions and reviewer mappings must be persistent."""
    project = ProjectRepository(db_session).create("CampusFlow", "discord")
    reviewers = ReviewerRepository(db_session)
    reviewer = reviewers.add(project.id, 100, "리뷰어")
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

    reviews.update_status(review, "APPROVED", changed_by_discord_id="100")

    assert reviewers.list_for_project(project.id) == [reviewer]
    assert reviews.find_by_resource("github", "org/repo:pr:42") is review
    assert reviews.find_by_discord_thread(300) is review
    assert reviews.list_open(project.id) == [review]
    assert reviewer.enabled is True
    assert reviewers.remove(project.id, 100) is True
