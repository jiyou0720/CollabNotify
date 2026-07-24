"""Administrator maintenance slash commands."""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from app.bot.checks import require_guild, server_manager_only
from app.bot.error_handling import respond_to_command_error
from app.services.administration_service import AdministrationService

logger = logging.getLogger(__name__)


class AdminCommandGroup(
    app_commands.Group,
    name="admin",
    description="CollabNotify 운영 상태를 관리합니다.",
):
    """Expose administrator-only maintenance commands."""

    def __init__(self, service: AdministrationService) -> None:
        super().__init__()
        self._service = service

    @app_commands.command(
        name="sync", description="명령 목록을 Discord와 동기화합니다."
    )
    @server_manager_only
    async def sync(self, interaction: discord.Interaction) -> None:
        """Synchronize commands for the current guild."""
        guild = require_guild(interaction)
        tree = interaction.client.tree
        tree.copy_global_to(guild=guild)
        commands = await tree.sync(guild=guild)
        await interaction.response.send_message(
            f"명령 {len(commands)}개를 동기화했습니다.", ephemeral=True
        )

    @app_commands.command(
        name="cleanup", description="유효하지 않은 채널 연결을 정리합니다."
    )
    @server_manager_only
    async def cleanup(self, interaction: discord.Interaction) -> None:
        """Remove stale channel mappings."""
        guild = require_guild(interaction)
        removed = self._service.cleanup(guild)
        await interaction.response.send_message(
            f"유효하지 않은 채널 연결 {removed}개를 정리했습니다.",
            ephemeral=True,
        )

    @app_commands.command(name="status", description="시스템 운영 상태를 확인합니다.")
    @server_manager_only
    async def status(self, interaction: discord.Interaction) -> None:
        """Display operational status."""
        guild = require_guild(interaction)
        current = self._service.status(guild.id, interaction.client.latency)
        embed = discord.Embed(
            title="CollabNotify 운영 상태", color=discord.Color.green()
        )
        embed.add_field(
            name="데이터베이스", value="정상" if current.database_ok else "오류"
        )
        embed.add_field(name="프로젝트", value=f"{current.project_count}개")
        embed.add_field(name="진행 중 리뷰", value=f"{current.open_review_count}개")
        embed.add_field(name="Discord 지연 시간", value=f"{current.latency_ms}ms")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Return Korean administrative command errors."""
        await respond_to_command_error(
            interaction, error, logger, "관리 명령을 처리하지 못했습니다."
        )
