"""Initialize the configured CollabNotify database schema."""

import os

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv


def main() -> None:
    """Upgrade the configured database to the latest migration revision."""
    load_dotenv()
    database_url = os.getenv("DATABASE_URL", "sqlite:///database/collabnotify.db")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")


if __name__ == "__main__":
    main()
