"""Tests for project command registration and Korean UI metadata."""

from sqlalchemy.orm import Session

from app.bot.bot import DiscordClient
from app.config.settings import BotConfig
from database.session import create_session_factory


def test_project_commands_are_registered_in_korean(db_session: Session) -> None:
    """Every required project subcommand must be present with Korean text."""
    client = DiscordClient(
        BotConfig(token="test-token", guild_id=123),
        create_session_factory(db_session.get_bind()),
    )

    group = client.tree.get_command("project")
    assert group is not None
    assert "프로젝트" in group.description
    assert {command.name for command in group.commands} == {
        "create",
        "delete",
        "archive",
        "restore",
        "list",
        "info",
        "map",
        "unmap",
    }
    assert all(
        any("가" <= char <= "힣" for char in command.description)
        for command in group.commands
    )

    review_group = client.tree.get_command("review")
    assert review_group is not None
    assert {command.name for command in review_group.commands} == {
        "approve",
        "reject",
        "status",
        "close",
    }
    expected_groups = {
        "project",
        "review",
        "admin",
        "settings",
        "test",
    }
    assert {command.name for command in client.tree.get_commands()} == expected_groups
    assert all(
        any("가" <= char <= "힣" for char in group.description)
        for group in client.tree.get_commands()
    )
    assert all(
        any("가" <= char <= "힣" for char in command.description)
        for group in client.tree.get_commands()
        for command in group.commands
    )
    assert {command.name for command in client.tree.get_command("admin").commands} == {
        "sync",
        "cleanup",
        "status",
    }
    assert {
        command.name for command in client.tree.get_command("settings").commands
    } == {"reviewers", "notifications", "archive-days", "auto-thread"}
    assert {command.name for command in client.tree.get_command("test").commands} == {
        "github",
        "jira",
        "confluence",
    }
    for group_name in ("project", "admin", "settings", "test"):
        group = client.tree.get_command(group_name)
        assert group is not None
        assert all(command.checks for command in group.commands)
    review_commands = {
        command.name: command for command in client.tree.get_command("review").commands
    }
    assert review_commands["close"].checks
