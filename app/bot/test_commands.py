"""Administrator notification preview slash commands."""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from app.bot.checks import server_manager_only
from app.bot.error_handling import respond_to_command_error
from app.core.enums import ServiceType
from app.schemas.common import Notification, NotificationAction, NotificationField
from app.services.embed_builder import EmbedBuilder

logger = logging.getLogger(__name__)


class TestCommandGroup(
    app_commands.Group,
    name="test",
    description="서비스별 Discord 알림을 미리 확인합니다.",
):
    """Render production Embed templates without external webhooks."""

    def __init__(self, embed_builder: EmbedBuilder | None = None) -> None:
        super().__init__()
        self._embed_builder = embed_builder or EmbedBuilder()

    @app_commands.command(name="github", description="GitHub 알림 예시를 전송합니다.")
    @server_manager_only
    async def github(self, interaction: discord.Interaction) -> None:
        """Send a Korean GitHub preview."""
        await self._send_preview(interaction, ServiceType.GITHUB)

    @app_commands.command(name="jira", description="Jira 알림 예시를 전송합니다.")
    @server_manager_only
    async def jira(self, interaction: discord.Interaction) -> None:
        """Send a Korean Jira preview."""
        await self._send_preview(interaction, ServiceType.JIRA)

    @app_commands.command(
        name="confluence", description="Confluence 알림 예시를 전송합니다."
    )
    @server_manager_only
    async def confluence(self, interaction: discord.Interaction) -> None:
        """Send a Korean Confluence preview."""
        await self._send_preview(interaction, ServiceType.CONFLUENCE)

    async def _send_preview(
        self, interaction: discord.Interaction, service: ServiceType
    ) -> None:
        labels = {
            ServiceType.GITHUB: ("GitHub 테스트 알림", "저장소"),
            ServiceType.JIRA: ("Jira 테스트 알림", "프로젝트"),
            ServiceType.CONFLUENCE: ("Confluence 테스트 알림", "스페이스"),
        }
        title, field_name = labels[service]
        notification = Notification(
            service=service,
            event_type="test",
            title=title,
            description="알림 설정이 정상적으로 동작합니다.",
            fields=(NotificationField(name=field_name, value="CollabNotify"),),
            actions=(NotificationAction(label="원본 열기", url="https://example.com"),),
        )
        await interaction.response.send_message(
            embed=self._embed_builder.build(notification),
            view=self._embed_builder.build_view(notification),
            ephemeral=True,
        )

    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Return safe Korean preview-command errors."""
        await respond_to_command_error(
            interaction, error, logger, "테스트 알림을 만들지 못했습니다."
        )
