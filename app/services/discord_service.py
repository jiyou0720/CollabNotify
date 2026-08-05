"""Low-level Discord API operations."""

from __future__ import annotations

import discord

from app.core.exceptions import ChannelNotFoundError
from app.services.channel_service import ChannelService


class DiscordService:
    """Encapsulate Discord message API calls."""

    def __init__(self, channel_service: ChannelService) -> None:
        """Initialize with a Discord channel resolver."""
        self._channel_service = channel_service

    async def send_embed(
        self,
        channel_id: int,
        embed: discord.Embed,
        view: discord.ui.View | None = None,
        content: str | None = None,
    ) -> discord.Message:
        """Send an Embed to a resolved messageable channel."""
        channel = self._channel_service.get_channel(channel_id)
        send = getattr(channel, "send", None)
        if send is None:
            raise ChannelNotFoundError(
                f"Discord channel {channel_id} cannot receive messages."
            )
        message = await send(
            content=content,
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                users=True,
                roles=True,
                replied_user=False,
            ),
        )
        if not isinstance(message, discord.Message):
            raise TypeError("Discord send operation returned an invalid message.")
        return message

    async def send_message(self, channel_id: int, content: str) -> discord.Message:
        """Send a plain text message."""
        channel = self._channel_service.get_channel(channel_id)
        send = getattr(channel, "send", None)
        if send is None:
            raise ChannelNotFoundError(
                f"Discord channel {channel_id} cannot receive messages."
            )
        message = await send(
            content,
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                users=True,
                roles=True,
                replied_user=False,
            ),
        )
        if not isinstance(message, discord.Message):
            raise TypeError("Discord send operation returned an invalid message.")
        return message

    @staticmethod
    async def edit_message(
        message: discord.Message,
        embed: discord.Embed,
        view: discord.ui.View | None = None,
    ) -> discord.Message:
        """Edit an existing Discord message."""
        return await message.edit(embed=embed, view=view)

    @staticmethod
    async def delete_message(message: discord.Message) -> None:
        """Delete an existing Discord message."""
        await message.delete()

    @staticmethod
    async def create_thread(
        message: discord.Message,
        title: str,
        auto_archive_duration: int = 1440,
    ) -> discord.Thread:
        """Create a public review thread from a notification message."""
        return await message.create_thread(
            name=title[:100],
            auto_archive_duration=auto_archive_duration,
            reason="CollabNotify 자동 리뷰 스레드",
        )

    async def create_channel_thread(
        self,
        channel_id: int,
        title: str,
        auto_archive_duration: int = 1440,
    ) -> discord.Thread:
        """Create a standalone public thread in a resolved text channel."""
        channel = self._channel_service.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            raise ChannelNotFoundError(
                f"Discord channel {channel_id} cannot create public threads."
            )
        return await channel.create_thread(
            name=title[:100],
            type=discord.ChannelType.public_thread,
            auto_archive_duration=auto_archive_duration,
            reason="CollabNotify 자동 리뷰 스레드",
        )

    @staticmethod
    async def send_thread_message(thread: discord.Thread, content: str) -> None:
        """Post a safe system message inside a review thread."""
        await thread.send(
            content,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    def get_thread(self, thread_id: int) -> discord.Thread:
        """Resolve a review thread from the Discord channel cache."""
        channel = self._channel_service.get_channel(thread_id)
        if not isinstance(channel, discord.Thread):
            raise ChannelNotFoundError(f"Discord channel {thread_id} is not a thread.")
        return channel

    async def archive_thread(self, thread_id: int) -> None:
        """Post completion notice and archive a review thread."""
        thread = self.get_thread(thread_id)
        await self.send_thread_message(
            thread, "✅ 리뷰가 완료되어 스레드를 보관했습니다."
        )
        await thread.edit(
            archived=True,
            locked=False,
            reason="CollabNotify 리뷰 완료",
        )

    async def set_thread_archived(
        self, thread_id: int, *, archived: bool, reason: str
    ) -> None:
        """Change a thread's archived state without adding presentation text."""
        thread = self.get_thread(thread_id)
        await thread.edit(archived=archived, locked=False, reason=reason)

    async def edit_channel_message(
        self,
        channel_id: int,
        message_id: int,
        embed: discord.Embed,
        view: discord.ui.View | None = None,
    ) -> discord.Message:
        """Fetch and update a previously delivered parent-channel message."""
        channel = self._channel_service.get_channel(channel_id)
        fetch_message = getattr(channel, "fetch_message", None)
        if fetch_message is None:
            raise ChannelNotFoundError(
                f"Discord channel {channel_id} cannot fetch messages."
            )
        message = await fetch_message(message_id)
        if not isinstance(message, discord.Message):
            raise TypeError("Discord fetch operation returned an invalid message.")
        return await message.edit(embed=embed, view=view)

    @staticmethod
    def mention_user(user_id: int) -> str:
        """Create a Discord user mention without accepting arbitrary markup."""
        if user_id <= 0:
            raise ValueError("user_id must be a positive integer.")
        return f"<@{user_id}>"

    @staticmethod
    def mention_role(role_id: int) -> str:
        """Create a Discord role mention without accepting arbitrary markup."""
        if role_id <= 0:
            raise ValueError("role_id must be a positive integer.")
        return f"<@&{role_id}>"
