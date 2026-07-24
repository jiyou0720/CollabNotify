# Installation

Requirements: Python 3.12, pip, and optionally Docker Compose v2.

1. Create a Python 3.12 virtual environment and install the reproducibly pinned
   packages in `requirements.txt`.
2. Copy `.env.example` to `.env`.
3. Set Discord and all three webhook secrets; use long independent random values.
4. Set `DATABASE_URL`; keep SQLite on persistent storage.
5. Run `python -m alembic upgrade head`.
6. Start `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`.
7. Confirm `/health`, then configure provider webhook URLs and run Discord tests.

For containers, run `docker compose up --build -d`. The entrypoint migrates before
starting. SQLite and logs use the Docker-managed `runtime_data` and
`runtime_logs` volumes, which remain writable by the non-root UID 10001. Put
HTTPS and request-size controls at a reverse proxy. Do not expose `.env`,
database files, or logs publicly.

Upgrade by backing up data, deploying the new image/code, applying Alembic, and
checking health and `/admin status`. Roll back application code only with a
database-compatible release; database downgrades require an explicit tested plan.

## Environment variables

| Variable | Purpose |
|---|---|
| `DISCORD_TOKEN` | Discord bot credential |
| `DISCORD_GUILD_ID` | Optional guild-scoped command sync |
| `ENABLE_DISCORD_BOT` | Enable Gateway client in API lifecycle |
| `GITHUB_WEBHOOK_SECRET` | GitHub HMAC secret |
| `JIRA_WEBHOOK_SECRET` | Jira shared secret |
| `CONFLUENCE_WEBHOOK_SECRET` | Confluence shared secret |
| `DATABASE_URL` | SQLAlchemy connection URL |
| `DOCKER_DATABASE_URL` | Optional container DB URL; defaults to `/app/data/collabnotify.db` |
| `LOG_LEVEL` | Application log threshold |

## Testing guide

Run `pytest` for all unit/API/integration tests, then the coverage command in the
README. Run Black, isort, Ruff, and `pip check`; every command must succeed before
deployment. Tests use isolated temporary SQLite databases and mocked Discord
objects, so they do not require production credentials.
