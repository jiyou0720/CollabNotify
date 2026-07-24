"""Tests for Discord bot environment settings."""

import pytest

from app.config.settings import BotConfig


def test_config_reads_required_and_optional_values() -> None:
    """Environment values must be normalized and converted."""
    config = BotConfig.from_env(
        environ={
            "DISCORD_TOKEN": " token-value ",
            "DISCORD_GUILD_ID": "123456",
            "LOG_LEVEL": "debug",
        }
    )

    assert config.token == "token-value"
    assert config.guild_id == 123456
    assert config.log_level == "DEBUG"


def test_config_allows_missing_guild_id() -> None:
    """Guild restriction is optional for initial client login."""
    config = BotConfig.from_env(environ={"DISCORD_TOKEN": "token-value"})

    assert config.guild_id is None
    assert config.log_level == "INFO"


def test_config_rejects_missing_token() -> None:
    """Client startup must fail early when no token is configured."""
    with pytest.raises(ValueError, match="DISCORD_TOKEN"):
        BotConfig.from_env(environ={})


def test_config_repr_does_not_expose_token() -> None:
    """Diagnostic output must never reveal the Discord token."""
    config = BotConfig(token="sensitive-token", guild_id=123)

    assert "sensitive-token" not in repr(config)


@pytest.mark.parametrize("guild_id", ["abc", "0", "-1"])
def test_config_rejects_invalid_guild_id(guild_id: str) -> None:
    """Discord identifiers must be positive integers."""
    with pytest.raises(ValueError, match="positive integer"):
        BotConfig.from_env(
            environ={"DISCORD_TOKEN": "token", "DISCORD_GUILD_ID": guild_id}
        )
