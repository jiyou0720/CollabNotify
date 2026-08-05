"""Discord client construction and lifecycle management."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from sqlalchemy.orm import Session, sessionmaker

from app.bot.admin_commands import AdminCommandGroup
from app.bot.project_commands import ProjectCommandGroup
from app.bot.review_commands import ReviewCommandGroup
from app.bot.settings_commands import SettingsCommandGroup
from app.bot.test_commands import TestCommandGroup
from app.config.settings import BotConfig
from app.services.administration_service import AdministrationService
from app.services.channel_service import ChannelService
from app.services.discord_service import DiscordService
from app.services.project_alias_service import ProjectAliasService
from app.services.project_management_service import ProjectManagementService
from app.services.review_thread_service import ReviewThreadService


def create_intents() -> discord.Intents:
    """Create the minimum intents required for guild and channel discovery."""
    intents = discord.Intents.none()
    intents.guilds = True
    return intents


class DiscordClient(discord.Client):
    """Discord client foundation without message or event behavior."""

    def __init__(
        self,
        config: BotConfig,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        """Initialize the Discord client and its channel resolver."""
        super().__init__(intents=create_intents())
        self.config = config
        self.channel_service = ChannelService(self, guild_id=config.guild_id)
        self.tree = app_commands.CommandTree(self)
        if session_factory is not None:
            discord_service = DiscordService(self.channel_service)
            administration_service = AdministrationService(session_factory)
            self.tree.add_command(
                ProjectCommandGroup(
                    ProjectManagementService(session_factory),
                    ProjectAliasService(session_factory),
                )
            )
            self.tree.add_command(
                ReviewCommandGroup(
                    ReviewThreadService(session_factory, discord_service)
                )
            )
            self.tree.add_command(AdminCommandGroup(administration_service))
            self.tree.add_command(SettingsCommandGroup(administration_service))
            self.tree.add_command(TestCommandGroup())

    async def setup_hook(self) -> None:
        """Synchronize registered commands before the client becomes ready."""
        if self.config.guild_id is not None:
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


class DiscordBotApplication:
    """Own the Discord client startup and graceful shutdown lifecycle."""

    def __init__(
        self,
        config: BotConfig,
        client: DiscordClient | None = None,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        """Initialize the application with an injectable Discord client."""
        self._config = config
        self.client = client or DiscordClient(config, session_factory)
        self._logger = logging.getLogger(__name__)

    async def run(self) -> None:
        """Connect to Discord and always close the client during shutdown."""
        self._logger.info("Starting Discord client.")
        try:
            await self.client.start(self._config.token)
        finally:
            if not self.client.is_closed():
                await self.client.close()
            self._logger.info("Discord client stopped.")
