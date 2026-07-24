"""Discord channel lookup and permission validation."""

from __future__ import annotations

import logging

import discord

from app.core.exceptions import ChannelNotFoundError

type DiscordChannel = (
    discord.abc.GuildChannel | discord.Thread | discord.abc.PrivateChannel
)


class ChannelService:
    """Resolve channels from the connected Discord client's local cache."""

    def __init__(self, client: discord.Client, guild_id: int | None = None) -> None:
        """Initialize a channel resolver for one Discord client."""
        self._client = client
        self._guild_id = guild_id
        self._channels: dict[int, DiscordChannel] = {}
        self._logger = logging.getLogger(__name__)

    def get_channel(self, channel_id: int) -> DiscordChannel:
        """Return a cached Discord channel and validate bot visibility."""
        if channel_id <= 0:
            raise ValueError("channel_id must be a positive integer.")

        cached_channel = self._channels.get(channel_id)
        if cached_channel is not None:
            return cached_channel

        channel = self._client.get_channel(channel_id)
        if channel is None:
            raise ChannelNotFoundError(
                f"Discord channel {channel_id} was not found in cache."
            )

        self._validate_guild(channel)
        self._validate_permissions(channel)
        self._channels[channel_id] = channel
        self._logger.debug("Cached Discord channel %s.", channel_id)
        return channel

    def clear_cache(self) -> None:
        """Clear the service-level channel cache."""
        self._channels.clear()

    def _validate_guild(self, channel: DiscordChannel) -> None:
        """Ensure the channel belongs to the configured guild when applicable."""
        if self._guild_id is None or isinstance(channel, discord.abc.PrivateChannel):
            return

        guild = getattr(channel, "guild", None)
        if guild is None or guild.id != self._guild_id:
            raise LookupError(
                f"Discord channel does not belong to guild {self._guild_id}."
            )

    @staticmethod
    def _validate_permissions(channel: DiscordChannel) -> None:
        """Ensure the bot can view, send, and embed in a guild channel."""
        if isinstance(channel, discord.abc.PrivateChannel):
            return

        guild = getattr(channel, "guild", None)
        bot_member = getattr(guild, "me", None)
        permissions_for = getattr(channel, "permissions_for", None)
        if bot_member is None or permissions_for is None:
            raise PermissionError("Discord bot guild membership is unavailable.")

        permissions = permissions_for(bot_member)
        required = {
            "view_channel": "view the target channel",
            "send_messages": "send messages to the target channel",
            "embed_links": "embed links in the target channel",
        }
        for permission, description in required.items():
            if not getattr(permissions, permission, False):
                raise PermissionError(f"Discord bot cannot {description}.")
