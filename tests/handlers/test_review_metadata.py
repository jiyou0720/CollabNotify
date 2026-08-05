"""Master-specification tests for automatic review-thread metadata."""

import pytest

from app.handlers.base_handler import BaseHandler
from app.handlers.confluence.handler import ConfluenceHandler
from app.handlers.github.handler import GithubHandler
from app.handlers.jira.handler import JiraHandler


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("event_type", "payload"),
    (
        (
            "issues",
            {
                "action": "opened",
                "repository": {"full_name": "org/repo"},
                "issue": {"number": 1, "title": "Issue"},
            },
        ),
        (
            "pull_request",
            {
                "action": "opened",
                "repository": {"full_name": "org/repo"},
                "pull_request": {"number": 2, "title": "PR"},
            },
        ),
        (
            "release",
            {
                "action": "created",
                "repository": {"full_name": "org/repo"},
                "release": {"tag_name": "v1.0.0"},
            },
        ),
        (
            "workflow_run",
            {
                "action": "completed",
                "repository": {"full_name": "org/repo"},
                "workflow_run": {
                    "id": 3,
                    "name": "CI",
                    "conclusion": "failure",
                },
            },
        ),
    ),
)
async def test_required_github_events_open_reviews(
    event_type: str, payload: dict[str, object]
) -> None:
    """Every GitHub event named by the master prompt must open a review."""
    notification = await GithubHandler(event_type).handle(payload)

    assert notification.review_action == "OPEN"
    assert notification.external_resource_id
    assert notification.review_thread_title


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("event_type", "expected_action"),
    (("jira:issue_created", "OPEN"), ("jira:issue_updated", "APPEND")),
)
async def test_required_jira_events_use_review_timeline(
    event_type: str, expected_action: str
) -> None:
    """Creation opens one review and later updates append to it."""
    notification = await JiraHandler(event_type).handle(
        {
            "issue": {
                "key": "CN-1",
                "fields": {
                    "summary": "Issue",
                    "project": {"name": "CollabNotify"},
                    "assignee": {"displayName": "Reviewer"},
                    "status": {"name": "In Progress"},
                },
            },
            "changelog": {
                "items": [
                    {
                        "field": "assignee",
                        "fromString": None,
                        "toString": "Reviewer",
                    }
                ]
            },
        }
    )

    assert notification.review_action == expected_action
    assert notification.external_resource_id == "CN-1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("event_type", "content_key"),
    (
        ("page_created", "page"),
        ("page_updated", "page"),
        ("page_deleted", "page"),
        ("comment_created", "comment"),
        ("attachment_created", "attachment"),
    ),
)
async def test_required_confluence_events_use_one_review_thread(
    event_type: str, content_key: str
) -> None:
    """Every Confluence event named by the master prompt must open a review."""
    payload: dict[str, object] = {
        "page": {"id": "10", "title": "시스템 설계"},
        "space": {"name": "Development"},
    }
    if content_key == "comment":
        payload[content_key] = {"id": "20", "body": "검토 의견"}
    elif content_key == "attachment":
        payload[content_key] = {"id": "30", "title": "diagram.png"}

    notification = await ConfluenceHandler(event_type).handle(payload)

    expected_action = "OPEN" if event_type == "page_created" else "APPEND"
    assert notification.review_action == expected_action
    assert notification.external_resource_id == "10"
    assert notification.review_thread_title


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler", "payload", "expected_action"),
    (
        (
            GithubHandler("issues"),
            {
                "action": "closed",
                "repository": {"full_name": "org/repo"},
                "issue": {"number": 1, "title": "Issue"},
            },
            "CLOSE",
        ),
        (
            GithubHandler("pull_request"),
            {
                "action": "closed",
                "repository": {"full_name": "org/repo"},
                "pull_request": {"number": 2, "title": "PR", "merged": True},
            },
            "APPEND",
        ),
    ),
)
async def test_required_completion_events_close_reviews(
    handler: BaseHandler, payload: dict[str, object], expected_action: str
) -> None:
    """GitHub completion events use their resource-specific lifecycle action."""
    notification = await handler.handle(payload)

    assert notification.review_action == expected_action
