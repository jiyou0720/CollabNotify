"""SQLAlchemy engine creation."""

import logging
from sqlite3 import Connection as SQLiteConnection

from sqlalchemy import Engine, create_engine, event

logger = logging.getLogger(__name__)


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine with SQLite integrity settings."""
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    engine = create_engine(database_url, echo=echo, connect_args=connect_args)
    logger.info("Database engine created: dialect=%s", engine.dialect.name)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(
            connection: SQLiteConnection, _record: object
        ) -> None:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine
