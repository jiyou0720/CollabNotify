"""Tests for low-level Discord operations."""

from unittest.mock import AsyncMock, Mock

import discord
import pytest

from app.core.exceptions import ChannelNotFoundError
from app.services.discord_service import DiscordService


@pytest.mark.asyncio
async def test_send_embed_uses_resolved_channel() -> None:
    """DiscordService must delegate Embed delivery to the target channel."""
    message = Mock(spec=discord.Message)
    channel = Mock()
    channel.send = AsyncMock(return_value=message)
    channel_service = Mock()
    channel_service.get_channel.return_value = channel
    service = DiscordService(channel_service)
    embed = discord.Embed(title="Test")

    result = await service.send_embed(100, embed)

    assert result is message
    channel_service.get_channel.assert_called_once_with(100)
    channel.send.assert_awaited_once()
    kwargs = channel.send.await_args.kwargs
    assert kwargs["content"] is None
    assert kwargs["embed"] is embed
    assert kwargs["view"] is None
    assert kwargs["allowed_mentions"].everyone is False


@pytest.mark.asyncio
async def test_send_embed_rejects_non_messageable_channel() -> None:
    """Channels without send capability must fail clearly."""
    channel_service = Mock()
    channel_service.get_channel.return_value = object()

    with pytest.raises(ChannelNotFoundError, match="cannot receive"):
        await DiscordService(channel_service).send_embed(100, discord.Embed())


@pytest.mark.asyncio
async def test_set_thread_archived_uses_resolved_thread() -> None:
    """Timeline lifecycle changes remain behind DiscordService."""
    thread = Mock(spec=discord.Thread)
    thread.edit = AsyncMock()
    channel_service = Mock()
    channel_service.get_channel.return_value = thread
    service = DiscordService(channel_service)

    await service.set_thread_archived(300, archived=False, reason="테스트")

    thread.edit.assert_awaited_once_with(archived=False, locked=False, reason="테스트")


@pytest.mark.asyncio
async def test_create_channel_thread_uses_text_channel() -> None:
    """A PR can create its thread without posting a parent message."""
    thread = Mock(spec=discord.Thread)
    channel = Mock(spec=discord.TextChannel)
    channel.create_thread = AsyncMock(return_value=thread)
    channel_service = Mock()
    channel_service.get_channel.return_value = channel
    service = DiscordService(channel_service)

    result = await service.create_channel_thread(100, "PR #123", 1440)

    assert result is thread
    channel.create_thread.assert_awaited_once_with(
        name="PR #123",
        type=discord.ChannelType.public_thread,
        auto_archive_duration=1440,
        reason="CollabNotify 자동 리뷰 스레드",
    )


@pytest.mark.asyncio
async def test_create_channel_thread_rejects_non_text_channel() -> None:
    """Standalone reviews require a Discord text channel."""
    channel_service = Mock()
    channel_service.get_channel.return_value = object()

    with pytest.raises(ChannelNotFoundError, match="cannot create public threads"):
        await DiscordService(channel_service).create_channel_thread(100, "PR #123")


@pytest.mark.asyncio
async def test_edit_channel_message_fetches_and_edits_parent() -> None:
    """Parent embed updates reuse the original Discord message."""
    message = Mock(spec=discord.Message)
    message.edit = AsyncMock(return_value=message)
    channel = Mock()
    channel.fetch_message = AsyncMock(return_value=message)
    channel_service = Mock()
    channel_service.get_channel.return_value = channel
    embed = discord.Embed(title="최신 상태")

    result = await DiscordService(channel_service).edit_channel_message(100, 200, embed)

    assert result is message
    channel.fetch_message.assert_awaited_once_with(200)
    message.edit.assert_awaited_once_with(embed=embed, view=None)


@pytest.mark.asyncio
async def test_edit_channel_message_rejects_non_fetchable_channel() -> None:
    """Parent updates fail clearly when message history is unavailable."""
    channel_service = Mock()
    channel_service.get_channel.return_value = object()

    with pytest.raises(ChannelNotFoundError, match="cannot fetch messages"):
        await DiscordService(channel_service).edit_channel_message(
            100, 200, discord.Embed()
        )


@pytest.mark.asyncio
async def test_edit_channel_message_rejects_invalid_fetch_result() -> None:
    """A malformed Discord fetch result cannot be treated as a message."""
    channel = Mock()
    channel.fetch_message = AsyncMock(return_value=object())
    channel_service = Mock()
    channel_service.get_channel.return_value = channel

    with pytest.raises(TypeError, match="invalid message"):
        await DiscordService(channel_service).edit_channel_message(
            100, 200, discord.Embed()
        )
