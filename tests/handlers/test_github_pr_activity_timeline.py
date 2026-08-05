"""GitHub pull-request activity timeline normalization tests."""

import pytest

from app.handlers.github.handler import GithubHandler


def pull_request_payload(action: str, **extra: object) -> dict[str, object]:
    """Build a representative pull-request webhook payload."""
    payload: dict[str, object] = {
        "action": action,
        "repository": {"full_name": "org/repo"},
        "sender": {"login": "author"},
        "pull_request": {
            "number": 123,
            "title": "Improve login",
            "user": {"login": "author"},
            "merged": False,
            "base": {"ref": "main"},
            "head": {"ref": "feature"},
        },
    }
    payload.update(extra)
    return payload


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action",
    (
        "edited",
        "synchronize",
        "reopened",
        "ready_for_review",
        "converted_to_draft",
        "review_requested",
        "review_request_removed",
        "labeled",
        "unlabeled",
        "assigned",
        "unassigned",
        "locked",
        "unlocked",
    ),
)
async def test_subsequent_pr_actions_append_without_parent_delivery(
    action: str,
) -> None:
    """Every non-final PR action targets the existing review thread only."""
    extras: dict[str, object] = {}
    if action in {"labeled", "unlabeled"}:
        extras["label"] = {"name": "bug"}
    elif action in {"assigned", "unassigned"}:
        extras["assignee"] = {"login": "developer"}
    elif action in {"review_requested", "review_request_removed"}:
        extras["requested_reviewer"] = {"login": "reviewer"}
    notification = await GithubHandler("pull_request").handle(
        pull_request_payload(action, **extras)
    )

    assert notification.external_resource_id == "org/repo:pr:123"
    assert notification.review_action == "APPEND"
    assert notification.parent_delivery is False
    assert len(notification.activities) == 1


@pytest.mark.asyncio
async def test_pr_open_and_completion_parent_delivery_contract() -> None:
    """Open creates one thread while closed and merged remain parent events."""
    opened = await GithubHandler("pull_request").handle(pull_request_payload("opened"))
    closed = await GithubHandler("pull_request").handle(pull_request_payload("closed"))
    merged_payload = pull_request_payload("closed")
    merged_payload["pull_request"]["merged"] = True
    merged = await GithubHandler("pull_request").handle(merged_payload)

    assert opened.review_action == "OPEN"
    assert opened.parent_delivery is True
    assert opened.activities[0].kind == "github_pr_opened"
    assert closed.title == "🔒 PR 종료"
    assert closed.activities[0].kind == "github_pr_closed"
    assert merged.title == "✅ PR 병합"
    assert "Merged by author" in merged.description
    assert merged.activities[0].kind == "github_pr_merged"
    assert merged.parent_update is True


@pytest.mark.asyncio
async def test_pr_open_contains_rich_parent_fields() -> None:
    """The initial PR embed has every required collaboration field."""
    payload = pull_request_payload("opened")
    pull_request = payload["pull_request"]
    pull_request["state"] = "open"
    pull_request["requested_reviewers"] = [{"login": "reviewer"}]

    notification = await GithubHandler("pull_request").handle(payload)
    fields = {field.name: field.value for field in notification.fields}

    assert fields["저장소"] == "org/repo"
    assert fields["PR"] == "#123"
    assert fields["제목"] == "Improve login"
    assert fields["작성자"] == "author"
    assert fields["작업 브랜치"] == "feature"
    assert fields["기준 브랜치"] == "main"
    assert fields["리뷰어"] == "reviewer"
    assert fields["현재 상태"] == "OPEN"


@pytest.mark.asyncio
async def test_synchronize_normalizes_compact_commit_summary() -> None:
    """Synchronize creates one activity containing compact commit lines."""
    payload = pull_request_payload(
        "synchronize",
        before="a" * 40,
        after="b" * 40,
        commits=[
            {
                "id": "abcdef123456",
                "author": {"name": "홍길동"},
                "message": "Fix login bug\n\nMore detail",
            },
            {
                "id": "1234567890ab",
                "author": {"name": "김철수"},
                "message": "Add tests",
            },
        ],
    )
    notification = await GithubHandler("pull_request").handle(payload)
    activity = notification.activities[0]

    assert activity.kind == "github_push"
    assert activity.after == "bbbbbbb"
    assert "`abcdef1` · 홍길동 · Fix login bug" in (activity.body or "")
    assert len(notification.activities) == 1


@pytest.mark.asyncio
async def test_synchronize_without_commit_list_uses_head_fallback() -> None:
    """Standard synchronize payloads still produce one useful commit line."""
    notification = await GithubHandler("pull_request").handle(
        pull_request_payload(
            "synchronize",
            after="abcdef1234567890",
        )
    )

    activity = notification.activities[0]
    assert activity.after == "abcdef1"
    assert "`abcdef1` · author · 커밋 메시지 정보 없음" in (activity.body or "")


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ("approved", "changes_requested"))
async def test_review_targets_existing_pr_thread(state: str) -> None:
    """Submitted review state is retained for Korean presentation."""
    notification = await GithubHandler("pull_request_review").handle(
        {
            "action": "submitted",
            "repository": {"full_name": "org/repo"},
            "pull_request": {"number": 123},
            "review": {
                "state": state,
                "body": "검토 의견",
                "user": {"login": "reviewer"},
            },
        }
    )

    assert notification.external_resource_id == "org/repo:pr:123"
    assert notification.parent_delivery is False
    assert notification.activities[0].after == state


@pytest.mark.asyncio
@pytest.mark.parametrize("event_type", ("pull_request_review_comment", "issue_comment"))
async def test_pr_comments_target_existing_thread(event_type: str) -> None:
    """Inline and general PR comments share the same PR resource mapping."""
    payload: dict[str, object] = {
        "action": "created",
        "repository": {"full_name": "org/repo"},
        "comment": {"body": "의견", "user": {"login": "reviewer"}},
    }
    if event_type == "pull_request_review_comment":
        payload["pull_request"] = {"number": 123}
    else:
        payload["issue"] = {"number": 123, "pull_request": {"url": "api"}}

    notification = await GithubHandler(event_type).handle(payload)

    assert notification.external_resource_id == "org/repo:pr:123"
    assert notification.review_action == "APPEND"
    assert notification.parent_delivery is False
