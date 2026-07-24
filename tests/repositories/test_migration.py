"""Tests for the initial Alembic migration."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_initial_migration_upgrades_and_downgrades(tmp_path: Path) -> None:
    """The initial migration must create and remove the complete schema."""
    database_path = tmp_path / "migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    inspector = inspect(engine)
    assert "projects" in inspector.get_table_names()
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
