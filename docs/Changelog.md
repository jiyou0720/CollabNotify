# Changelog

## Production audit

- Added bounded streaming for webhook request bodies, ambiguous cross-guild
  routing rejection, idempotent terminal review states, shared Korean command
  error handling, project lifecycle rollback tests, pinned dependencies, and
  removal of a redundant review-thread index in Alembic revision `0004`.

## Phase 14

- Added automatic review threads for specified GitHub, Jira, and Confluence
  events, Korean checklists, five persisted states, manual review commands, and
  automatic completion archiving.
- Added reviewer, notification, auto-thread, and archive-period settings plus
  administrator synchronization, cleanup, status, and provider test commands.
- Localized all Discord-facing UI in Korean.

## Phase 13

- Added the complete `/project` command group, managed category/channel creation,
  provider mappings, confirmed deletion, archive/restore, listing, and detail UI.
- Added project lifecycle and channel mapping persistence with Alembic revision
  `0003_project_reviews`.

## Phases 1-12

- Established Python 3.12 structure, Discord client, FastAPI API, authenticated
  webhook handlers, SQLAlchemy repositories, delivery coordination, embeds,
  logging, retries, migrations, tests, and Docker deployment.

## Future improvements

- PostgreSQL support for horizontally scaled production deployments.
- Distributed background queue and delivery metrics dashboards.
- Per-project checklist templates and reviewer escalation policies.
- Additional collaboration providers without changing the normalized event API.
