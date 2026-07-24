"""Reusable Discord application-command permission checks."""

import discord
from discord import app_commands

from app.core.exceptions import InvalidConfigurationError


def is_server_manager(interaction: discord.Interaction) -> bool:
    """Return whether the caller can administer or manage the guild."""
    permissions = getattr(interaction.user, "guild_permissions", None)
    return bool(permissions and (permissions.administrator or permissions.manage_guild))


server_manager_only = app_commands.check(is_server_manager)


def require_guild(interaction: discord.Interaction) -> discord.Guild:
    """Return the interaction guild or raise a Korean configuration error."""
    if interaction.guild is None:
        raise InvalidConfigurationError("서버에서만 사용할 수 있는 명령입니다.")
    return interaction.guild
