"""Discord review lifecycle slash commands."""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from app.bot.checks import server_manager_only
from app.bot.error_handling import respond_to_command_error
from app.core.exceptions import InvalidConfigurationError
from app.services.review_thread_service import (
    REVIEW_STATUS_LABELS,
    ReviewThreadService,
)

logger = logging.getLogger(__name__)


class ReviewCommandGroup(
    app_commands.Group,
    name="review",
    description="현재 리뷰 스레드의 상태를 관리합니다.",
):
    """Expose review decisions within registered Discord threads."""

    def __init__(self, service: ReviewThreadService) -> None:
        super().__init__()
        self._service = service

    @app_commands.command(name="approve", description="현재 리뷰를 승인합니다.")
    @app_commands.describe(note="선택적인 승인 의견")
    async def approve(
        self, interaction: discord.Interaction, note: str | None = None
    ) -> None:
        """Mark the current review as approved."""
        await self._set_status(interaction, "APPROVED", note)

    @app_commands.command(
        name="reject", description="수정 요청 또는 반려로 처리합니다."
    )
    @app_commands.describe(decision="처리 상태", note="수정 요청 또는 반려 사유")
    @app_commands.choices(
        decision=[
            app_commands.Choice(name="수정 요청", value="CHANGES_REQUESTED"),
            app_commands.Choice(name="반려", value="REJECTED"),
        ]
    )
    async def reject(
        self,
        interaction: discord.Interaction,
        decision: app_commands.Choice[str] | None = None,
        note: str | None = None,
    ) -> None:
        """Request changes or mark the current review as rejected."""
        status = decision.value if decision is not None else "REJECTED"
        await self._set_status(interaction, status, note)

    @app_commands.command(name="status", description="현재 리뷰 상태를 확인합니다.")
    async def status(self, interaction: discord.Interaction) -> None:
        """Display current persisted review status."""
        thread_id = self._require_thread(interaction)
        review = self._service.get_status(thread_id)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="리뷰 상태",
                description=REVIEW_STATUS_LABELS[review.status],
                color=discord.Color.gold(),
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="close", description="리뷰를 완료하고 스레드를 보관합니다."
    )
    @server_manager_only
    async def close(self, interaction: discord.Interaction) -> None:
        """Complete and archive the current review thread."""
        thread_id = self._require_thread(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self._service.update_status(
            thread_id,
            "COMPLETED",
            interaction.user.id,
        )
        await interaction.followup.send(
            "리뷰를 완료하고 스레드를 보관했습니다.", ephemeral=True
        )

    async def _set_status(
        self,
        interaction: discord.Interaction,
        status: str,
        note: str | None,
    ) -> None:
        thread_id = self._require_thread(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self._service.update_status(
            thread_id,
            status,
            interaction.user.id,
            note,
        )
        await interaction.followup.send(
            f"리뷰 상태를 {REVIEW_STATUS_LABELS[status]}(으)로 변경했습니다.",
            ephemeral=True,
        )

    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Return safe Korean errors for review commands."""
        await respond_to_command_error(
            interaction,
            error,
            logger,
            "리뷰 명령을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        )

    @staticmethod
    def _require_thread(interaction: discord.Interaction) -> int:
        if not isinstance(interaction.channel, discord.Thread):
            raise InvalidConfigurationError(
                "등록된 리뷰 스레드 안에서만 사용할 수 있습니다."
            )
        return interaction.channel.id
