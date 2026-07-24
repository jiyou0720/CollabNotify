"""Korean Discord interaction views."""

from __future__ import annotations

import discord


class DeleteConfirmationView(discord.ui.View):
    """Require the requesting administrator to confirm project deletion."""

    def __init__(self, requester_id: int) -> None:
        super().__init__(timeout=60)
        self.requester_id = requester_id
        self.confirmed = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Reject confirmation attempts from other users."""
        if interaction.user.id == self.requester_id:
            return True
        await interaction.response.send_message(
            "이 확인 작업은 명령을 실행한 관리자만 사용할 수 있습니다.",
            ephemeral=True,
        )
        return False

    @discord.ui.button(label="삭제 확인", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ) -> None:
        """Confirm deletion and wake the waiting command."""
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ) -> None:
        """Cancel deletion and wake the waiting command."""
        await interaction.response.defer()
        self.stop()
