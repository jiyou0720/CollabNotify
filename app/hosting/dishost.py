"""Run CollabNotify on a DisHost/Pterodactyl allocation."""

import logging
import os
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import load_dotenv
from pyngrok import conf, ngrok

from scripts.init_db import main as upgrade_database

LOGGER = logging.getLogger(__name__)
DEFAULT_PORT = 8000


def allocation_port(environment: dict[str, str] | None = None) -> int:
    """Return the configured Pterodactyl allocation port."""
    values = os.environ if environment is None else environment
    raw_port = next(
        (
            values[name]
            for name in ("DISHOST_PORT", "SERVER_PORT", "PORT")
            if values.get(name, "").strip()
        ),
        str(DEFAULT_PORT),
    )
    try:
        port = int(raw_port)
    except ValueError as error:
        raise ValueError(f"Server port must be a number: {raw_port!r}") from error
    if not 1 <= port <= 65535:
        raise ValueError(f"Server port must be between 1 and 65535: {port}")
    return port


def configure_persistent_database(environment: dict[str, str] | None = None) -> str:
    """Set a persistent SQLite URL when DATABASE_URL was not supplied."""
    values = os.environ if environment is None else environment
    configured = values.get("DATABASE_URL", "").strip()
    if configured:
        return configured

    container_root = Path(values.get("DISHOST_DATA_DIR", "/home/container/data"))
    container_root.mkdir(parents=True, exist_ok=True)
    database_url = f"sqlite:///{container_root.as_posix()}/collabnotify.db"
    values["DATABASE_URL"] = database_url
    return database_url


def ngrok_settings(
    environment: dict[str, str] | None = None,
) -> tuple[str, str, str] | None:
    """Validate and return ngrok settings without logging the auth token."""
    values = os.environ if environment is None else environment
    token = values.get("NGROK_AUTHTOKEN", "").strip()
    domain = values.get("NGROK_DOMAIN", "").strip()
    if not token and not domain:
        return None
    if not token or not domain:
        raise ValueError("NGROK_AUTHTOKEN and NGROK_DOMAIN must be set together.")

    executable = values.get(
        "NGROK_BIN", "/home/container/data/ngrok/ngrok"
    ).strip()
    return token, domain, executable


def start_ngrok(port: int) -> Any | None:
    """Download/start the optional ngrok agent and return its tunnel."""
    settings = ngrok_settings()
    if settings is None:
        LOGGER.warning(
            "ngrok is disabled; the allocation address must receive webhooks."
        )
        return None

    token, domain, executable = settings
    Path(executable).parent.mkdir(parents=True, exist_ok=True)
    config = conf.PyngrokConfig(ngrok_path=executable, auth_token=token)
    LOGGER.info("Starting ngrok for configured static domain on port %s.", port)
    return ngrok.connect(
        addr=str(port), proto="http", domain=domain, pyngrok_config=config
    )


def stop_ngrok(tunnel: Any | None) -> None:
    """Stop the ngrok tunnel during server shutdown."""
    if tunnel is None:
        return
    ngrok.disconnect(tunnel.public_url)
    ngrok.kill()


def main() -> None:
    """Prepare persistence, migrate the database, and serve CollabNotify."""
    load_dotenv()
    os.environ.setdefault("ENABLE_DISCORD_BOT", "true")
    port = allocation_port()
    configure_persistent_database()
    upgrade_database()
    tunnel = start_ngrok(port)
    try:
        uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info")
    finally:
        stop_ngrok(tunnel)
