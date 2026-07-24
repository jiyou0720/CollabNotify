"""Environment-backed settings for the Discord bot."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class BotConfig:
    """Configuration required to connect the Discord client."""

    token: str = field(repr=False)
    guild_id: int | None = None
    log_level: str = "INFO"

    @classmethod
    def from_env(
        cls,
        env_file: str | Path = ".env",
        environ: Mapping[str, str] | None = None,
    ) -> BotConfig:
        """Create bot settings from a mapping or the process environment."""
        if environ is None:
            load_dotenv(dotenv_path=env_file)
            environ = os.environ

        token = environ.get("DISCORD_TOKEN", "").strip()
        if not token:
            raise ValueError("DISCORD_TOKEN must be configured.")

        guild_id = cls._parse_guild_id(environ.get("DISCORD_GUILD_ID", ""))
        log_level = environ.get("LOG_LEVEL", "INFO").strip().upper() or "INFO"

        return cls(token=token, guild_id=guild_id, log_level=log_level)

    @staticmethod
    def _parse_guild_id(raw_guild_id: str) -> int | None:
        """Parse and validate an optional Discord guild identifier."""
        value = raw_guild_id.strip()
        if not value:
            return None

        try:
            guild_id = int(value)
        except ValueError as exc:
            raise ValueError("DISCORD_GUILD_ID must be a positive integer.") from exc

        if guild_id <= 0:
            raise ValueError("DISCORD_GUILD_ID must be a positive integer.")

        return guild_id


@dataclass(frozen=True, slots=True)
class WebhookConfig:
    """Secrets used to authenticate inbound webhook requests."""

    github_secret: str = field(repr=False)
    jira_secret: str = field(repr=False)
    confluence_secret: str = field(repr=False)

    @classmethod
    def from_env(
        cls,
        env_file: str | Path = ".env",
        environ: Mapping[str, str] | None = None,
    ) -> WebhookConfig:
        """Load all webhook secrets and reject incomplete configuration."""
        if environ is None:
            load_dotenv(dotenv_path=env_file)
            environ = os.environ

        names = (
            "GITHUB_WEBHOOK_SECRET",
            "JIRA_WEBHOOK_SECRET",
            "CONFLUENCE_WEBHOOK_SECRET",
        )
        values = {name: environ.get(name, "").strip() for name in names}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ValueError(f"Missing webhook secrets: {', '.join(missing)}")

        return cls(
            github_secret=values["GITHUB_WEBHOOK_SECRET"],
            jira_secret=values["JIRA_WEBHOOK_SECRET"],
            confluence_secret=values["CONFLUENCE_WEBHOOK_SECRET"],
        )
