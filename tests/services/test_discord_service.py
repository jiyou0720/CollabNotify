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
