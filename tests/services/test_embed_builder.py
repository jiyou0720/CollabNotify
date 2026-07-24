"""Tests for Discord Embed and link-button rendering."""

from datetime import UTC, datetime

import discord
import pytest

from app.core.enums import ServiceType
from app.schemas.common import Notification, NotificationAction, NotificationField
from app.services.embed_builder import SERVICE_COLORS, EmbedBuilder


def create_notification(
    service: ServiceType,
    *,
    event_type: str = "event",
    title: str = "Event Created",
    description: str = "An event occurred.",
    fields: tuple[NotificationField, ...] = (),
    actions: tuple[NotificationAction, ...] = (),
) -> Notification:
    """Create a deterministic Notification for rendering tests."""
    return Notification(
        service=service,
        event_type=event_type,
        title=title,
        description=description,
        fields=fields,
        actions=actions,
        timestamp=datetime(2026, 7, 24, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    ("service", "icon"),
    [
        (ServiceType.GITHUB, "🟣"),
        (ServiceType.JIRA, "🔵"),
        (ServiceType.CONFLUENCE, "🟢"),
    ],
)
def test_service_embed_uses_ui_specification(service: ServiceType, icon: str) -> None:
    """Each service must use its icon, color, footer, and timestamp."""
    notification = create_notification(
        service,
        fields=(NotificationField(name="Project", value="CollabNotify"),),
    )

    embed = EmbedBuilder().build(notification)

    assert embed.title == f"{icon} Event Created"
    assert embed.color.value == SERVICE_COLORS[service]
    assert embed.footer.text == f"CollabNotify • {service.value.title()}"
    assert embed.timestamp == notification.timestamp
    assert embed.fields[0].name == "Project"
    assert embed.thumbnail.url


def test_workflow_failure_uses_error_color() -> None:
    """Failed workflows must render with the documented red color."""
    notification = create_notification(
        ServiceType.GITHUB,
        event_type="workflow_run",
        fields=(NotificationField(name="Result", value="failure"),),
    )

    embed = EmbedBuilder().build(notification)

    assert embed.color.value == 0xE74C3C


def test_embed_truncates_long_content() -> None:
    """Descriptions and fields must remain within Discord limits."""
    notification = create_notification(
        ServiceType.JIRA,
        description="d" * 600,
        fields=(NotificationField(name="Field", value="v" * 1100),),
    )

    embed = EmbedBuilder().build(notification)

    assert len(embed.description or "") == 500
    assert (embed.description or "").endswith("...")
    assert len(embed.fields[0].value) == 1024


def test_build_view_creates_link_buttons() -> None:
    """Notification actions must become URL-only Discord buttons."""
    notification = create_notification(
        ServiceType.CONFLUENCE,
        actions=(
            NotificationAction(
                label="Open Document", url="https://confluence.example/page"
            ),
        ),
    )

    view = EmbedBuilder().build_view(notification)

    assert view is not None
    assert len(view.children) == 1
    button = view.children[0]
    assert isinstance(button, discord.ui.Button)
    assert button.style is discord.ButtonStyle.link
    assert button.url == "https://confluence.example/page"


def test_build_view_returns_none_without_actions() -> None:
    """Notifications without links must not create empty Views."""
    notification = create_notification(ServiceType.GITHUB)

    assert EmbedBuilder().build_view(notification) is None
