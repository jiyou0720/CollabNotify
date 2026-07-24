"""Tests for Discord client construction and lifecycle."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.bot.bot import DiscordBotApplication, DiscordClient, create_intents
from app.config.settings import BotConfig


def test_create_intents_enables_only_guild_discovery() -> None:
    """The bot must not subscribe to messages or privileged events."""
    intents = create_intents()

    assert intents.guilds is True
    assert intents.guild_messages is False
    assert intents.dm_messages is False
    assert intents.message_content is False
    assert intents.members is False
    assert intents.presences is False


def test_discord_client_initializes_channel_service() -> None:
    """The client must expose its Phase 2 channel resolver."""
    config = BotConfig(token="test-token", guild_id=123)

    client = DiscordClient(config)

    assert client.config is config
    assert client.channel_service is not None
    assert client.intents.guilds is True


@pytest.mark.asyncio
async def test_application_starts_and_closes_client() -> None:
    """The lifecycle must close Discord after the client stops."""
    config = BotConfig(token="test-token")
    client = Mock(spec=DiscordClient)
    client.start = AsyncMock()
    client.close = AsyncMock()
    client.is_closed.return_value = False
    application = DiscordBotApplication(config, client=client)

    await application.run()

    client.start.assert_awaited_once_with("test-token")
    client.close.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_application_closes_client_after_start_failure() -> None:
    """A connection failure must still trigger graceful client cleanup."""
    config = BotConfig(token="test-token")
    client = Mock(spec=DiscordClient)
    client.start = AsyncMock(side_effect=RuntimeError("connection failed"))
    client.close = AsyncMock()
    client.is_closed.return_value = False
    application = DiscordBotApplication(config, client=client)

    with pytest.raises(RuntimeError, match="connection failed"):
        await application.run()

    client.close.assert_awaited_once_with()
