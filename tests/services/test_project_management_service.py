"""Tests for Discord project server management."""

from unittest.mock import AsyncMock, Mock

import discord
import pytest
from sqlalchemy.orm import Session

from app.repositories.channel_repository import ChannelRepository
from app.repositories.project_repository import ProjectRepository
from app.services.project_management_service import (
    DEFAULT_PROJECT_CHANNELS,
    ProjectManagementService,
)
from database.session import create_session_factory


def make_guild() -> tuple[Mock, Mock, dict[str, Mock]]:
    """Create a Discord guild double with category and channel resources."""
    guild = Mock(spec=discord.Guild)
    guild.id = 10
    category = Mock(spec=discord.CategoryChannel)
    category.id = 20
    category.name = "CampusFlow"
    category.delete = AsyncMock()
    channels: dict[str, Mock] = {}
    for index, name in enumerate(DEFAULT_PROJECT_CHANNELS, start=30):
        channel = Mock(spec=discord.TextChannel)
        channel.id = index
        channel.name = name
        channel.mention = f"<#{index}>"
        channel.guild = guild
        channel.delete = AsyncMock()
        channel.edit = AsyncMock()
        channels[name] = channel
    guild.create_category = AsyncMock(return_value=category)
    guild.create_text_channel = AsyncMock(
        side_effect=[channels[name] for name in DEFAULT_PROJECT_CHANNELS]
    )
    guild.get_channel = Mock(
        side_effect=lambda channel_id: (
            category
            if channel_id == category.id
            else next(
                (channel for channel in channels.values() if channel.id == channel_id),
                None,
            )
        )
    )
    guild.categories = []
    return guild, category, channels


@pytest.mark.asyncio
async def test_create_project_builds_default_discord_space(
    db_session: Session,
) -> None:
    """Project creation must build all six channels and persist mappings."""
    guild, category, channels = make_guild()
    factory = create_session_factory(db_session.get_bind())
    service = ProjectManagementService(factory)

    result = await service.create_project(guild, "CampusFlow")

    assert result.category is category
    assert set(result.channels) == set(DEFAULT_PROJECT_CHANNELS)
    assert guild.create_text_channel.await_count == 6
    with factory() as session:
        project = ProjectRepository(session).find_managed("CampusFlow", 10)
        assert project is not None
        mappings = ChannelRepository(session).list_for_project(project.id)
    assert {mapping.service for mapping in mappings} == set(channels)


@pytest.mark.asyncio
async def test_archive_and_restore_project_moves_channels(
    db_session: Session,
) -> None:
    """Archive must disable delivery and restore must reverse the operation."""
    guild, category, channels = make_guild()
    archive = Mock(spec=discord.CategoryChannel)
    archive.id = 99
    archive.name = "📦 Archived"
    guild.categories = [archive]
    factory = create_session_factory(db_session.get_bind())
    service = ProjectManagementService(factory)
    await service.create_project(guild, "CampusFlow")

    archived = await service.archive_project(guild, "CampusFlow")
    restored = await service.restore_project(guild, "CampusFlow")

    assert archived.status == "ARCHIVED"
    assert archived.enabled is False
    assert restored.status == "ACTIVE"
    assert restored.enabled is True
    for channel in channels.values():
        assert channel.edit.await_count == 2


@pytest.mark.asyncio
async def test_restore_reuses_existing_project_category_after_partial_retry(
    db_session: Session,
) -> None:
    """Restore retries must not create duplicate project categories."""
    guild, original_category, channels = make_guild()
    archive = Mock(spec=discord.CategoryChannel)
    archive.id = 99
    archive.name = "📦 Archived"
    recovered = Mock(spec=discord.CategoryChannel)
    recovered.id = 21
    recovered.name = "CampusFlow"
    factory = create_session_factory(db_session.get_bind())
    service = ProjectManagementService(factory)
    await service.create_project(guild, "CampusFlow")
    guild.categories = [archive]
    await service.archive_project(guild, "CampusFlow")

    guild.categories = [archive, recovered]
    guild.get_channel = Mock(
        side_effect=lambda channel_id: next(
            (channel for channel in channels.values() if channel.id == channel_id),
            None,
        )
    )
    restored = await service.restore_project(guild, "CampusFlow")

    assert restored.discord_category_id == str(recovered.id)
    assert guild.create_category.await_count == 1
    assert original_category is not recovered


@pytest.mark.asyncio
async def test_delete_project_removes_discord_resources_and_database(
    db_session: Session,
) -> None:
    """Confirmed deletion must remove channels, category, and configuration."""
    guild, category, channels = make_guild()
    factory = create_session_factory(db_session.get_bind())
    service = ProjectManagementService(factory)
    await service.create_project(guild, "CampusFlow")

    await service.delete_project(guild, "CampusFlow")

    for channel in channels.values():
        channel.delete.assert_awaited_once()
    category.delete.assert_awaited_once()
    with factory() as session:
        assert ProjectRepository(session).find_managed("CampusFlow", 10) is None


@pytest.mark.asyncio
async def test_create_project_rolls_back_partial_discord_resources(
    db_session: Session,
) -> None:
    """A failed channel creation must clean up every resource already created."""
    guild, category, channels = make_guild()
    created = [channels["general"], channels["github"]]
    guild.create_text_channel = AsyncMock(
        side_effect=[*created, RuntimeError("Discord unavailable")]
    )
    factory = create_session_factory(db_session.get_bind())
    service = ProjectManagementService(factory)

    with pytest.raises(RuntimeError, match="Discord unavailable"):
        await service.create_project(guild, "CampusFlow")

    for channel in created:
        channel.delete.assert_awaited_once()
    category.delete.assert_awaited_once()
    with factory() as session:
        assert ProjectRepository(session).find_managed("CampusFlow", 10) is None


def test_project_channel_map_and_unmap(db_session: Session) -> None:
    """Administrators must be able to replace and remove a service mapping."""
    factory = create_session_factory(db_session.get_bind())
    with factory.begin() as session:
        ProjectRepository(session).create(
            "CampusFlow",
            "discord",
            "discord:10:campusflow",
            discord_guild_id="10",
            discord_category_id="20",
        )
    service = ProjectManagementService(factory)
    channel = Mock(spec=discord.TextChannel)
    channel.id = 30
    channel.name = "github"
    channel.guild = Mock()
    channel.guild.id = 10

    service.map_channel(10, "CampusFlow", "github", channel)

    assert service.unmap_channel(10, "CampusFlow", "github") is True
    assert service.unmap_channel(10, "CampusFlow", "github") is False
