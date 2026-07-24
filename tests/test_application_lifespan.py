"""Tests for the combined API and Discord Bot lifecycle."""

import asyncio
from typing import ClassVar
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.config.settings import BotConfig
from app.main import create_app


class FakeBotApplication:
    """Controllable Bot application used for lifespan tests."""

    started: ClassVar[bool] = False
    stopped: ClassVar[bool] = False

    def __init__(self, config: BotConfig, **_kwargs: object) -> None:
        self.config = config
        self.client = Mock()
        self.client.channel_service = Mock()
        self.client.wait_until_ready = self.wait_until_ready

    async def run(self) -> None:
        """Run until the FastAPI lifespan cancels this task."""
        type(self).started = True
        try:
            await asyncio.Future()
        finally:
            type(self).stopped = True

    async def wait_until_ready(self) -> None:
        """Expose the same readiness boundary as discord.Client."""
        while not type(self).started:
            await asyncio.sleep(0)


def test_lifespan_starts_and_stops_enabled_bot(monkeypatch) -> None:
    """Container mode must own the Discord Bot task lifecycle."""
    FakeBotApplication.started = False
    FakeBotApplication.stopped = False
    monkeypatch.setenv("ENABLE_DISCORD_BOT", "true")
    monkeypatch.setenv("DISCORD_TOKEN", "test-token")
    monkeypatch.setenv("DISCORD_GUILD_ID", "123")
    monkeypatch.setattr("app.main.DiscordBotApplication", FakeBotApplication)

    with TestClient(create_app()) as client:
        assert client.get("/health").status_code == 200
        assert FakeBotApplication.started is True

    assert FakeBotApplication.stopped is True
