"""Shared Korean Discord application-command error responses."""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from app.core.exceptions import InvalidConfigurationError


async def respond_to_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
    logger: logging.Logger,
    fallback_message: str,
) -> None:
    """Log one command failure and return a safe Korean ephemeral response."""
    original = getattr(error, "original", error)
    if isinstance(original, (InvalidConfigurationError, ValueError)):
        message = str(original)
    elif isinstance(error, app_commands.CheckFailure):
        message = "이 명령은 관리자 또는 서버 관리 권한이 필요합니다."
    else:
        logger.error(
            "Discord application command failed: %s",
            original,
            exc_info=(type(original), original, original.__traceback__),
        )
        message = fallback_message
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)
