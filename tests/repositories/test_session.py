"""Tests for database initialization and transaction boundaries."""

import pytest
from sqlalchemy import inspect, text

from app.models import Base
from database.database import create_database_engine
from database.session import create_session_factory, session_scope


def test_model_metadata_contains_all_documented_tables() -> None:
    """ORM metadata must contain every documented table."""
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    assert set(inspect(engine).get_table_names()) == {
        "channel_mappings",
        "change_requests",
        "error_logs",
        "notification_logs",
        "projects",
        "project_aliases",
        "review_completions",
        "review_statuses",
        "review_threads",
        "reviewer_mappings",
        "role_mappings",
        "settings",
        "user_mappings",
    }
    engine.dispose()


def test_session_scope_commits_and_rolls_back() -> None:
    """Transaction scope must commit success and roll back failure."""
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE values_table (value INTEGER)"))
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        session.execute(text("INSERT INTO values_table VALUES (1)"))

    with pytest.raises(RuntimeError):
        with session_scope(factory) as session:
            session.execute(text("INSERT INTO values_table VALUES (2)"))
            raise RuntimeError("rollback")

    with engine.connect() as connection:
        values = list(connection.scalars(text("SELECT value FROM values_table")))
    assert values == [1]
    engine.dispose()
