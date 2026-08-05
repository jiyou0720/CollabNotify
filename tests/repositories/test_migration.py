"""Tests for the initial Alembic migration."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_initial_migration_upgrades_and_downgrades(tmp_path: Path) -> None:
    """The initial migration must create and remove the complete schema."""
    database_path = tmp_path / "migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    inspector = inspect(engine)
    assert "projects" in inspector.get_table_names()
    assert "project_aliases" in inspector.get_table_names()
    assert "notification_logs" in inspector.get_table_names()
    assert "review_threads" in inspector.get_table_names()
    assert "reviewer_mappings" in inspector.get_table_names()
    assert "review_statuses" in inspector.get_table_names()
    assert "idx_user_service" in {
        index["name"] for index in inspector.get_indexes("user_mappings")
    }
    review_indexes = {
        index["name"] for index in inspector.get_indexes("review_threads")
    }
    assert "idx_review_thread_status" in review_indexes
    assert "idx_review_thread_discord" not in review_indexes

    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()


def test_migration_honors_database_url_environment(tmp_path: Path, monkeypatch) -> None:
    """Deployment migrations must target DATABASE_URL, not the ini default."""
    database_path = tmp_path / "configured.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    config = Config("alembic.ini")

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    assert "projects" in inspect(engine).get_table_names()
    engine.dispose()


def test_alias_migration_preserves_unambiguous_managed_routes(tmp_path: Path) -> None:
    """Migration 0005 converts a legacy managed-project name route."""
    database_path = tmp_path / "legacy-alias.db"
    url = f"sqlite:///{database_path.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "0004")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("""
                INSERT INTO projects
                    (name, service, external_id, discord_guild_id,
                     discord_category_id, status, enabled, created_at, updated_at)
                VALUES
                    ('Org/Repo', 'discord', 'discord:1:org/repo', '1', '10',
                     'ACTIVE', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """))
        project_id = connection.execute(
            text("SELECT id FROM projects WHERE service = 'discord'")
        ).scalar_one()
        connection.execute(
            text("""
                INSERT INTO channel_mappings
                    (service, project_id, discord_channel_id, created_at)
                VALUES ('github', :project_id, '100', CURRENT_TIMESTAMP)
                """),
            {"project_id": project_id},
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        alias = connection.execute(
            text("SELECT project_id, provider, external_name FROM project_aliases")
        ).one()
    assert tuple(alias) == (project_id, "github", "org/repo")
    engine.dispose()
