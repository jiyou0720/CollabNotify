# Architecture

CollabNotify uses one FastAPI process with an optional Discord Gateway client.
FastAPI authenticates webhooks and schedules processing; handlers normalize
provider payloads into `Notification`; the dispatcher selects the handler; the
coordinator resolves database mappings and invokes Discord delivery. Successful
eligible notifications are passed to `ReviewThreadService`.

Dependencies point inward: API and Discord command adapters call services;
services call repositories and the Discord adapter; repositories alone access
SQLAlchemy sessions. Session factories are injected at application composition.

```text
GitHub/Jira/Confluence -> FastAPI -> WebhookService -> Dispatcher -> Handler
                                                        |
                                                        v
Database <- Repository <- Coordinator -> DiscordService -> Discord
                                      -> ReviewThreadService
Discord slash commands -> Project/Review/Administration services
```

Project categories contain `general`, `github`, `jira`, `confluence`, `meeting`,
and `release`. Archiving moves project channels to the shared `📦 Archived`
category and disables delivery; restoring reverses both operations.

Database schema changes are versioned in `database/migrations/versions`. Runtime
code never creates or alters schema. Provider payload processing is idempotent by
delivery identifier, and notification/thread failures are recorded without
duplicating already delivered Discord messages.

## Folder structure

```text
app/
  api/          FastAPI routes and dependencies
  bot/          Discord client, commands, checks, and views
  handlers/     Provider payload normalization
  models/       SQLAlchemy models
  repositories/ Persistence boundary
  services/     Application workflows and integrations
database/       Session setup and Alembic migrations
docs/           Design and operations documentation
tests/          Unit, API, integration, and deployment tests
```
