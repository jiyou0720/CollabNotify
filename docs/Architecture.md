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

Confluence lifecycle uses the common review-thread path without a provider-specific
database table:

```text
page_created -> ConfluenceHandler -> parent Embed -> ReviewThreadService
             -> review_threads(Page ID, message ID, Thread ID)
page_updated/comment/attachment -> Page ID lookup -> existing Thread activity
page_deleted -> deletion activity -> existing Thread archive
```

The handler accepts native Confluence `content`/`actor` payloads and normalized
Automation `page`/`user` payloads. Both become the same immutable Notification and
NotificationActivity schemas before Discord delivery.

`ThreadManager` is the provider-neutral lifecycle boundary. Its public contract is
`create_thread`, `find_thread`, `post_to_thread`, and `archive_thread`.
`ReviewThreadService` implements this contract and additionally translates normalized
activities into Korean timeline messages. GitHub, Jira, and Confluence enter through
the same `NotificationCoordinator`; provider handlers never call Discord or the thread
repository directly. This allows another provider to reuse the lifecycle without a
second thread implementation.

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

## Project alias routing

Webhook routing is independent from Discord's internal project names:

```text
Provider payload
  -> normalized external identifier
  -> ProjectAliasService
  -> project_aliases(provider, external_name)
  -> internal Discord Project
  -> provider ChannelMapping
  -> Discord notification
```

`NotificationCoordinator` depends on `ProjectAliasService`; it never searches a
`Project` by a provider name. An absent alias or unavailable target is logged and
treated as a safely ignored delivery. The `(provider, external_name)` uniqueness
constraint makes routing deterministic across Discord guilds.

## Jira Activity Timeline

Jira timeline processing preserves the existing dependency direction:

```text
JiraHandler
  -> Notification.activities
  -> WebhookService
  -> NotificationCoordinator
  -> ReviewThreadService
  -> DiscordService
```

`JiraHandler` converts tracked `changelog.items` into presentation-independent
`NotificationActivity` values. `ReviewThreadService` resolves the existing
`ReviewThread` using `(service, issue key)`, formats Korean timeline messages, and
owns completion/reopen state transitions. `DiscordService` remains the only layer
that accesses Discord thread APIs. Only `jira:issue_created` may create a thread;
later activity never creates a replacement when the mapping is absent.

## GitHub PR Activity Timeline

GitHub PR activity follows the same normalized collaboration path:

```text
GithubHandler
  -> Notification.activities + parent_delivery
  -> WebhookService
  -> NotificationCoordinator
  -> ReviewThreadService
  -> DiscordService
```

The review resource key is `<repository>:pr:<number>`. `opened` posts one rich parent
embed and creates the sole review thread from that message.
Subsequent PR, review, inline review-comment, and PR issue-comment notifications set
`parent_delivery=false`, update the existing parent embed when state changes, and
append activity only to the mapped thread. A final `closed` webhook updates the same
parent embed, distinguishes merged and unmerged completion, appends the result to the
thread, and archives it. Reopen always unarchives the same thread, including threads
automatically archived by Discord inactivity.
## Unified object thread lifecycle

GitHub PRs, Jira issues, and Confluence pages share the same lifecycle metadata:

- `review_action=OPEN`: deliver one parent embed and persist its message/thread IDs.
- `parent_update=true`: fetch and edit that parent message without a new delivery.
- `review_action=APPEND`: append normalized activities to the mapped thread.
- completion: update the parent, append completion, archive the same thread.
- reopen: unarchive the persisted thread instead of creating another one.

`ReviewThreadService.update_parent_message()` uses the existing
`ReviewThread.discord_message_id`. Missing legacy parent messages are logged and do not
prevent activity delivery. No database migration is required.
