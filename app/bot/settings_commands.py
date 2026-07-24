"""Administrator settings slash commands."""

from __future__ import annotations

import logging
from typing import Literal

import discord
from discord import app_commands

from app.bot.checks import require_guild, server_manager_only
from app.bot.error_handling import respond_to_command_error
from app.services.administration_service import AdministrationService

logger = logging.getLogger(__name__)


class SettingsCommandGroup(
    app_commands.Group,
    name="settings",
    description="알림과 리뷰 설정을 관리합니다.",
):
    """Expose persistent project and review settings."""

    def __init__(self, service: AdministrationService) -> None:
        super().__init__()
        self._service = service

    @app_commands.command(name="reviewers", description="프로젝트 리뷰어를 관리합니다.")
    @app_commands.describe(
        project_name="프로젝트명",
        action="추가, 삭제 또는 목록",
        user="추가하거나 삭제할 사용자",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="추가", value="add"),
            app_commands.Choice(name="삭제", value="remove"),
            app_commands.Choice(name="목록", value="list"),
        ]
    )
    @server_manager_only
    async def reviewers(
        self,
        interaction: discord.Interaction,
        project_name: str,
        action: app_commands.Choice[str],
        user: discord.Member | None = None,
    ) -> None:
        """Configure project reviewer mappings."""
        guild = require_guild(interaction)
        reviewer_ids = self._service.configure_reviewer(
            guild.id, project_name, action.value, user
        )
        if action.value == "list":
            message = (
                "등록된 리뷰어: "
                + " ".join(f"<@{user_id}>" for user_id in reviewer_ids)
                if reviewer_ids
                else "등록된 리뷰어가 없습니다."
            )
        elif action.value == "add":
            message = "리뷰어를 추가했습니다."
        else:
            message = "리뷰어를 삭제했습니다."
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(
        name="notifications", description="프로젝트 알림을 켜거나 끕니다."
    )
    @app_commands.describe(project_name="프로젝트명", enabled="알림 활성화 여부")
    @server_manager_only
    async def notifications(
        self,
        interaction: discord.Interaction,
        project_name: str,
        enabled: bool,
    ) -> None:
        """Enable or disable project notification delivery."""
        guild = require_guild(interaction)
        self._service.set_notifications(guild.id, project_name, enabled)
        state = "활성화" if enabled else "비활성화"
        await interaction.response.send_message(
            f"**{project_name}** 알림을 {state}했습니다.", ephemeral=True
        )

    @app_commands.command(
        name="archive-days", description="스레드 자동 보관 기간을 설정합니다."
    )
    @app_commands.describe(days="자동 보관 기간")
    @server_manager_only
    async def archive_days(
        self,
        interaction: discord.Interaction,
        days: Literal[1, 3, 7],
    ) -> None:
        """Set the automatic Discord thread archive duration."""
        self._service.set_archive_days(days)
        await interaction.response.send_message(
            f"스레드 자동 보관 기간을 {days}일로 설정했습니다.", ephemeral=True
        )

    @app_commands.command(
        name="auto-thread", description="자동 리뷰 스레드를 켜거나 끕니다."
    )
    @app_commands.describe(enabled="자동 스레드 활성화 여부")
    @server_manager_only
    async def auto_thread(
        self, interaction: discord.Interaction, enabled: bool
    ) -> None:
        """Enable or disable automatic review thread creation."""
        self._service.set_auto_thread(enabled)
        state = "활성화" if enabled else "비활성화"
        await interaction.response.send_message(
            f"자동 리뷰 스레드를 {state}했습니다.", ephemeral=True
        )

    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Return safe Korean settings errors."""
        await respond_to_command_error(
            interaction, error, logger, "설정 명령을 처리하지 못했습니다."
        )
