"""Tests for GitHub notification normalization."""

import pytest

from app.core.enums import ServiceType
from app.core.exceptions import PayloadValidationError, UnsupportedEventError
from app.handlers.github.handler import GithubHandler


@pytest.mark.asyncio
async def test_github_pull_request_notification() -> None:
    """Pull requests must produce a service-independent Notification."""
    payload = {
        "action": "opened",
        "repository": {"full_name": "org/repo"},
        "pull_request": {
            "number": 42,
            "title": "Add webhook support",
            "user": {"login": "developer"},
            "base": {"ref": "main"},
            "head": {"ref": "feature/webhooks"},
            "merged": False,
            "html_url": "https://github.example/pr/42",
        },
    }

    notification = await GithubHandler("pull_request").handle(payload)

    assert notification.service is ServiceType.GITHUB
    assert notification.title == "PR 생성"
    assert notification.actions[0].label == "PR 열기"
    assert {field.name: field.value for field in notification.fields}[
        "기준 브랜치"
    ] == "main"


@pytest.mark.asyncio
async def test_github_push_notification() -> None:
    """Push events must expose branch and commit count."""
    payload = {
        "ref": "refs/heads/main",
        "repository": {"name": "repo"},
        "commits": [{"id": "one"}, {"id": "two"}],
        "pusher": {"name": "developer"},
        "compare": "https://github.example/compare",
    }

    notification = await GithubHandler("push").handle(payload)
    fields = {field.name: field.value for field in notification.fields}

    assert fields["브랜치"] == "main"
    assert fields["커밋 수"] == "2"


@pytest.mark.asyncio
async def test_github_handler_rejects_missing_repository() -> None:
    """Required GitHub domain objects must be validated."""
    with pytest.raises(PayloadValidationError, match="repository"):
        await GithubHandler("issues").handle({"issue": {"number": 1}})


@pytest.mark.asyncio
async def test_github_handler_ignores_unsupported_action() -> None:
    """An event name alone must not allow undocumented provider actions."""
    with pytest.raises(UnsupportedEventError):
        await GithubHandler("issues").handle(
            {
                "action": "transferred",
                "repository": {"full_name": "org/repo"},
                "issue": {"number": 1, "title": "Issue"},
            }
        )
