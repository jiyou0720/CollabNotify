"""Tests for shared Korean Discord interaction safeguards."""

import logging
from unittest.mock import AsyncMock, Mock

import discord
import pytest
from discord import app_commands

from app.bot.checks import require_guild
from app.bot.error_handling import respond_to_command_error
from app.bot.views import DeleteConfirmationView
from app.core.exceptions import InvalidConfigurationError


@pytest.mark.asyncio
async def test_permission_failure_uses_korean_ephemeral_response() -> None:
    """Permission errors must never fall through to Discord's English default."""
    interaction = Mock(spec=discord.Interaction)
    interaction.response.is_done.return_value = False
    interaction.response.send_message = AsyncMock()

    await respond_to_command_error(
        interaction,
        app_commands.CheckFailure("denied"),
        logging.getLogger(__name__),
        "처리하지 못했습니다.",
    )

    interaction.response.send_message.assert_awaited_once_with(
        "이 명령은 관리자 또는 서버 관리 권한이 필요합니다.", ephemeral=True
    )


def test_require_guild_rejects_direct_messages_in_korean() -> None:
    """Guild-only commands must reject direct messages safely."""
    interaction = Mock(spec=discord.Interaction)
    interaction.guild = None

    with pytest.raises(InvalidConfigurationError, match="서버에서만"):
        require_guild(interaction)


@pytest.mark.asyncio
async def test_delete_confirmation_rejects_other_users() -> None:
    """Only the administrator who requested deletion may confirm it."""
    view = DeleteConfirmationView(requester_id=100)
    interaction = Mock(spec=discord.Interaction)
    interaction.user.id = 200
    interaction.response.send_message = AsyncMock()

    assert await view.interaction_check(interaction) is False
    interaction.response.send_message.assert_awaited_once()
