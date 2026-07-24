"""Discord Embed and link-button rendering."""

from __future__ import annotations

import discord

from app.core.enums import ServiceType
from app.schemas.common import Notification

SERVICE_COLORS = {
    ServiceType.GITHUB: 0x6F42C1,
    ServiceType.JIRA: 0x0052CC,
    ServiceType.CONFLUENCE: 0x008DA6,
}

SERVICE_ICONS = {
    ServiceType.GITHUB: "🟣",
    ServiceType.JIRA: "🔵",
    ServiceType.CONFLUENCE: "🟢",
}

THUMBNAIL_URLS = {
    ServiceType.GITHUB: "https://cdn.simpleicons.org/github",
    ServiceType.JIRA: "https://cdn.simpleicons.org/jira/0052CC",
    ServiceType.CONFLUENCE: "https://cdn.simpleicons.org/confluence/008DA6",
}


class EmbedBuilder:
    """Render normalized Notifications using the Discord UI specification."""

    def build(self, notification: Notification) -> discord.Embed:
        """Build a service-specific Discord Embed."""
        builders = {
            ServiceType.GITHUB: self.build_github,
            ServiceType.JIRA: self.build_jira,
            ServiceType.CONFLUENCE: self.build_confluence,
        }
        return builders[notification.service](notification)

    def build_github(self, notification: Notification) -> discord.Embed:
        """Build a GitHub Embed with result-aware colors."""
        color = SERVICE_COLORS[ServiceType.GITHUB]
        if notification.event_type == "release":
            color = 0x2ECC71
        elif notification.event_type == "workflow_run":
            result = (
                self._field_value(notification, "Result")
                or self._field_value(notification, "결과")
            ).lower()
            if result in {"failure", "failed"}:
                color = 0xE74C3C
            elif result in {"success", "succeeded"}:
                color = 0x2ECC71
        return self._build_embed(notification, color)

    def build_jira(self, notification: Notification) -> discord.Embed:
        """Build a Jira Embed."""
        color = SERVICE_COLORS[ServiceType.JIRA]
        if "priority" in notification.title.lower() or "우선순위" in notification.title:
            color = 0xF39C12
        return self._build_embed(notification, color)

    def build_confluence(self, notification: Notification) -> discord.Embed:
        """Build a Confluence Embed."""
        return self._build_embed(notification, SERVICE_COLORS[ServiceType.CONFLUENCE])

    def build_view(self, notification: Notification) -> discord.ui.View | None:
        """Build up to three link buttons for original-service navigation."""
        if not notification.actions:
            return None

        view = discord.ui.View(timeout=None)
        for action in notification.actions[:3]:
            view.add_item(
                discord.ui.Button(
                    label=self._truncate(action.label, 80),
                    style=discord.ButtonStyle.link,
                    url=str(action.url),
                )
            )
        return view

    def _build_embed(self, notification: Notification, color: int) -> discord.Embed:
        """Apply the shared Embed layout and accessibility rules."""
        icon = SERVICE_ICONS[notification.service]
        embed = discord.Embed(
            title=self._truncate(f"{icon} {notification.title}", 256),
            description=self._truncate(notification.description, 500),
            color=color,
            timestamp=notification.timestamp,
        )
        for field in notification.fields[:25]:
            embed.add_field(
                name=self._truncate(field.name, 256),
                value=self._truncate(field.value, 1024),
                inline=field.inline,
            )
        embed.set_footer(text=f"CollabNotify • {notification.service.value.title()}")
        embed.set_thumbnail(url=THUMBNAIL_URLS[notification.service])
        return embed

    @staticmethod
    def _field_value(notification: Notification, name: str) -> str:
        """Find a Notification field value by name."""
        for field in notification.fields:
            if field.name == name:
                return field.value
        return ""

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        """Truncate text with an ellipsis while respecting Discord limits."""
        if len(value) <= limit:
            return value
        return f"{value[: limit - 3]}..."
