# CollabNotify

CollabNotify receives collaboration events from GitHub, Jira, and Confluence
and delivers them to Discord. The project targets Python 3.12 and follows the
architecture and implementation sequence documented in `docs/`.

## Current implementation status

Phase 1 (Project Initialization) provides the project layout, dependency
manifest, environment template, and development-tool configuration. Discord,
FastAPI, webhook, database, and other application behavior belong to later
phases and are not implemented yet.

## Requirements

- Python 3.12.x
- Git
- Docker 27+ and Docker Compose v2 (required from the deployment phase)

## Setup

On Windows:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

On Linux or macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Fill in the local `.env` values before running functionality implemented in
later phases. Never commit `.env` or credentials.

## Phase 1 validation

```bash
python -m pytest
python -m black --check .
python -m ruff check .
python -m isort --check-only .
```

Application run commands will be added with the relevant implementation
phases.
