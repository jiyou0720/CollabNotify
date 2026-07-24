"""Shared pytest fixtures."""

from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from app.models import Base
from database.database import create_database_engine
from database.session import create_session_factory


@pytest.fixture
def db_session() -> Generator[Session]:
    """Provide an isolated in-memory SQLite Session."""
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
