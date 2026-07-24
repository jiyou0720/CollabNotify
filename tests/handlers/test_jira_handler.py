"""Tests for Jira notification normalization."""

import pytest

from app.core.enums import ServiceType
from app.handlers.jira.handler import JiraHandler


@pytest.mark.asyncio
async def test_jira_issue_created_notification() -> None:
    """Jira issues must expose project, status, and priority."""
    payload = {
        "issue": {
            "key": "CN-10",
            "self": "https://jira.example/CN-10",
            "fields": {
                "summary": "Create dispatcher",
                "project": {"name": "CollabNotify"},
                "reporter": {"displayName": "Reporter"},
                "assignee": {"displayName": "Developer"},
                "priority": {"name": "High"},
                "status": {"name": "To Do"},
            },
        }
    }

    notification = await JiraHandler("jira:issue_created").handle(payload)
    fields = {field.name: field.value for field in notification.fields}

    assert notification.service is ServiceType.JIRA
    assert notification.title == "이슈 생성"
    assert fields["이슈"] == "CN-10"
    assert fields["우선순위"] == "High"


@pytest.mark.asyncio
async def test_jira_update_includes_changelog() -> None:
    """Jira update descriptions must summarize changed values."""
    payload = {
        "issue": {"key": "CN-10", "fields": {"summary": "Update"}},
        "changelog": {
            "items": [
                {
                    "field": "status",
                    "fromString": "To Do",
                    "toString": "Done",
                }
            ]
        },
    }

    notification = await JiraHandler("jira:issue_updated").handle(payload)

    assert "status: To Do → Done" in notification.description
