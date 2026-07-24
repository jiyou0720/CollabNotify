"""Tests for the production Handler registry."""

from app.api.dependencies import get_event_dispatcher
from app.core.enums import ServiceType


def test_default_dispatcher_registers_every_documented_event() -> None:
    """Every MVP API event must have a concrete Handler."""
    get_event_dispatcher.cache_clear()
    dispatcher = get_event_dispatcher()
    events = {
        ServiceType.GITHUB: (
            "issues",
            "issue_comment",
            "pull_request",
            "pull_request_review",
            "push",
            "release",
            "workflow_run",
            "create",
            "delete",
        ),
        ServiceType.JIRA: (
            "jira:issue_created",
            "jira:issue_updated",
            "jira:issue_deleted",
            "comment_created",
            "comment_updated",
            "comment_deleted",
        ),
        ServiceType.CONFLUENCE: (
            "page_created",
            "page_updated",
            "comment_created",
            "attachment_created",
        ),
    }

    for service, service_events in events.items():
        for event_type in service_events:
            assert dispatcher.get_handler(service, event_type) is not None
