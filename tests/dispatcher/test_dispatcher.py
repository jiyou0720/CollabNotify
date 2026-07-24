"""Tests for event routing and Handler registration."""

from unittest.mock import AsyncMock

import pytest

from app.core.enums import ServiceType
from app.core.exceptions import UnsupportedEventError
from app.dispatcher.dispatcher import EventDispatcher


@pytest.mark.asyncio
async def test_dispatch_selects_registered_handler() -> None:
    """A service-event key must invoke exactly its registered Handler."""
    dispatcher = EventDispatcher()
    handler = AsyncMock()
    handler.handle.return_value = "notification"
    dispatcher.register(ServiceType.GITHUB, "pull_request", handler)
    payload = {"action": "opened"}

    result = await dispatcher.dispatch("GITHUB", " PULL_REQUEST ", payload)

    assert result == "notification"
    handler.handle.assert_awaited_once_with(payload)


@pytest.mark.asyncio
async def test_dispatch_rejects_unsupported_event() -> None:
    """An unregistered event must raise a meaningful exception."""
    dispatcher = EventDispatcher()

    with pytest.raises(UnsupportedEventError, match="github/issues"):
        await dispatcher.dispatch(ServiceType.GITHUB, "issues", {})


def test_detect_service_rejects_unknown_service() -> None:
    """Unknown collaboration services must be rejected."""
    with pytest.raises(UnsupportedEventError, match="Unsupported service"):
        EventDispatcher.detect_service("gitlab")


@pytest.mark.parametrize(
    ("service", "payload", "header", "expected"),
    [
        (ServiceType.GITHUB, {}, "Issues", "issues"),
        (
            ServiceType.JIRA,
            {"webhookEvent": "jira:issue_created"},
            None,
            "jira:issue_created",
        ),
        (ServiceType.CONFLUENCE, {"eventType": "page_updated"}, None, "page_updated"),
    ],
)
def test_detect_event_uses_service_convention(
    service: ServiceType,
    payload: dict[str, str],
    header: str | None,
    expected: str,
) -> None:
    """Event detection must use each service's documented identifier."""
    assert EventDispatcher.detect_event(service, payload, header) == expected


def test_register_replaces_same_event_handler() -> None:
    """Registry updates must deterministically replace the same key."""
    dispatcher = EventDispatcher()
    first_handler = AsyncMock()
    second_handler = AsyncMock()

    dispatcher.register(ServiceType.JIRA, "comment_created", first_handler)
    dispatcher.register(ServiceType.JIRA, "comment_created", second_handler)

    assert dispatcher.get_handler(ServiceType.JIRA, "comment_created") is second_handler
