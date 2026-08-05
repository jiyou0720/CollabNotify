"""Jira activity timeline normalization tests."""

import pytest

from app.handlers.jira.handler import JiraHandler


@pytest.mark.asyncio
async def test_jira_update_normalizes_all_tracked_changes() -> None:
    """Each required Jira changelog field becomes a separate activity."""
    fields = (
        ("status", "To Do", "In Progress"),
        ("assignee", None, "박지유"),
        ("priority", "Medium", "High"),
        ("summary", "Old", "New"),
        ("description", "Old description", "New description"),
        ("labels", "bug", "backend"),
        ("resolution", None, "Done"),
    )
    notification = await JiraHandler("jira:issue_updated").handle(
        {
            "user": {"displayName": "홍길동"},
            "issue": {
                "key": "CN-1",
                "fields": {"project": {"name": "CollabNotify"}},
            },
            "changelog": {
                "items": [
                    {"field": field, "fromString": before, "toString": after}
                    for field, before, after in fields
                ]
            },
        }
    )

    assert notification.review_action == "APPEND"
    assert notification.external_resource_id == "CN-1"
    assert [activity.kind for activity in notification.activities] == [
        field for field, _before, _after in fields
    ]
    assert all(activity.actor == "홍길동" for activity in notification.activities)
    labels = notification.activities[5]
    assert labels.added == ("backend",)
    assert labels.removed == ("bug",)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "event_type", ("comment_created", "comment_updated", "comment_deleted")
)
async def test_jira_comment_targets_issue_review_thread(event_type: str) -> None:
    """Every comment activity carries the parent issue key and author."""
    notification = await JiraHandler(event_type).handle(
        {
            "issue": {
                "key": "CN-1",
                "fields": {"project": {"name": "CollabNotify"}},
            },
            "comment": {
                "body": "검토 의견",
                "author": {"displayName": "홍길동"},
            },
        }
    )

    assert notification.review_action == "APPEND"
    assert notification.external_resource_id == "CN-1"
    assert notification.activities[0].kind == event_type
    assert notification.activities[0].actor == "홍길동"


@pytest.mark.asyncio
async def test_jira_issue_deletion_targets_existing_thread() -> None:
    """Issue deletion is represented as a timeline activity, not a new review."""
    notification = await JiraHandler("jira:issue_deleted").handle(
        {
            "user": {"displayName": "홍길동"},
            "issue": {
                "key": "CN-1",
                "fields": {"project": {"name": "CollabNotify"}},
            },
        }
    )

    assert notification.review_action == "APPEND"
    assert notification.external_resource_id == "CN-1"
    assert notification.activities[0].kind == "issue_deleted"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "comment_payload",
    (
        {
            "body": "자동 댓글",
            "author": {"displayName": "Automation for Jira", "accountType": "app"},
        },
        {
            "body": "시스템 댓글",
            "author": {"displayName": "System Bot"},
        },
    ),
)
async def test_jira_automation_comments_are_ignored(
    comment_payload: dict[str, object],
) -> None:
    """Automation and system comments never enter the issue timeline."""
    notification = await JiraHandler("comment_created").handle(
        {
            "issue": {
                "key": "CN-1",
                "fields": {"project": {"name": "CollabNotify"}},
            },
            "comment": comment_payload,
        }
    )

    assert notification.review_action == "NONE"
    assert notification.activities == ()
    assert notification.parent_delivery is False


@pytest.mark.asyncio
async def test_jira_issue_creation_comment_is_ignored() -> None:
    """Comments generated as part of issue creation are not duplicated."""
    notification = await JiraHandler("comment_created").handle(
        {
            "issue_event_type_name": "issue_created",
            "issue": {
                "key": "CN-1",
                "fields": {"project": {"name": "CollabNotify"}},
            },
            "comment": {
                "body": "생성 자동 댓글",
                "author": {"displayName": "홍길동"},
            },
        }
    )

    assert notification.review_action == "NONE"


@pytest.mark.asyncio
async def test_jira_flat_automation_comment_targets_issue_thread() -> None:
    """Automation scalar fields retain the issue key, author, and body."""
    notification = await JiraHandler("comment_created").handle(
        {
            "issueKey": "CN-42",
            "projectName": "CollabNotify",
            "issueUrl": "https://example.atlassian.net/browse/CN-42",
            "commentAuthor": "홍길동",
            "commentBody": "검토 의견입니다.",
        }
    )

    assert notification.external_resource_id == "CN-42"
    assert notification.review_action == "APPEND"
    assert notification.parent_delivery is False
    assert notification.activities[0].actor == "홍길동"
    assert notification.activities[0].body == "검토 의견입니다."


@pytest.mark.asyncio
async def test_jira_adf_comment_body_is_readable() -> None:
    """Native Jira ADF comments are converted to timeline text."""
    notification = await JiraHandler("comment_created").handle(
        {
            "issue": {
                "key": "CN-42",
                "fields": {"project": {"name": "CollabNotify"}},
            },
            "comment": {
                "author": {"displayName": "홍길동"},
                "body": {
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "검토 완료"}],
                        }
                    ],
                },
            },
        }
    )

    assert notification.activities[0].body == "검토 완료"
