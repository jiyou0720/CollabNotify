"""Tests for cached Discord channel resolution."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.channel_service import ChannelService


def create_channel(
    *,
    guild_id: int = 10,
    can_view: bool = True,
    can_send: bool = True,
    can_embed: bool = True,
) -> Mock:
    """Create a channel double with guild visibility information."""
    channel = Mock()
    channel.guild = SimpleNamespace(id=guild_id, me=object())
    channel.permissions_for.return_value = SimpleNamespace(
        view_channel=can_view,
        send_messages=can_send,
        embed_links=can_embed,
    )
    return channel


def test_get_channel_resolves_and_caches_channel() -> None:
    """Repeated lookup must use the service cache."""
    client = Mock()
    channel = create_channel()
    client.get_channel.return_value = channel
    service = ChannelService(client, guild_id=10)

    first_result = service.get_channel(100)
    second_result = service.get_channel(100)

    assert first_result is channel
    assert second_result is channel
    client.get_channel.assert_called_once_with(100)


def test_clear_cache_forces_client_lookup() -> None:
    """Clearing the service cache must force a fresh client lookup."""
    client = Mock()
    client.get_channel.return_value = create_channel()
    service = ChannelService(client, guild_id=10)

    service.get_channel(100)
    service.clear_cache()
    service.get_channel(100)

    assert client.get_channel.call_count == 2


def test_get_channel_rejects_unknown_channel() -> None:
    """A missing Discord cache entry must produce a clear lookup error."""
    client = Mock()
    client.get_channel.return_value = None
    service = ChannelService(client)

    with pytest.raises(LookupError, match="was not found"):
        service.get_channel(100)


def test_get_channel_rejects_other_guild() -> None:
    """Configured guild isolation must reject channels from other guilds."""
    client = Mock()
    client.get_channel.return_value = create_channel(guild_id=20)
    service = ChannelService(client, guild_id=10)

    with pytest.raises(LookupError, match="guild 10"):
        service.get_channel(100)


def test_get_channel_rejects_invisible_channel() -> None:
    """The bot must have permission to view a resolved guild channel."""
    client = Mock()
    client.get_channel.return_value = create_channel(can_view=False)
    service = ChannelService(client, guild_id=10)

    with pytest.raises(PermissionError, match="cannot view"):
        service.get_channel(100)


@pytest.mark.parametrize("permission", ["send", "embed"])
def test_get_channel_rejects_missing_delivery_permission(permission: str) -> None:
    """Sending requires send_messages and embed_links permissions."""
    client = Mock()
    client.get_channel.return_value = create_channel(
        can_send=permission != "send", can_embed=permission != "embed"
    )

    with pytest.raises(PermissionError):
        ChannelService(client, guild_id=10).get_channel(100)


def test_get_channel_rejects_non_positive_id() -> None:
    """Invalid Discord identifiers must fail before client lookup."""
    service = ChannelService(Mock())

    with pytest.raises(ValueError, match="positive integer"):
        service.get_channel(0)
