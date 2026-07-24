# Administrator Guide

Commands that mutate projects or system settings require Discord Administrator
or Manage Server permission.

- `/project create|delete|archive|restore|list|info|map|unmap`
- `/admin sync|cleanup|status`
- `/settings reviewers|notifications|archive-days|auto-thread`
- `/test github|jira|confluence`

Project creation builds one category and six channels and writes default
provider mappings. Deletion requires an explicit button confirmation and removes
Discord resources and dependent database configuration. Archive disables
notifications and moves channels under `📦 Archived`; restore recreates the
category association and enables delivery.

Run `/admin sync` after command deployment, `/admin cleanup` after manual Discord
channel deletion, and `/admin status` for database, project, open-review, and
Gateway latency checks. Configure auto-archive to 1, 3, or 7 days. Use test
commands after mapping changes; they send Korean preview embeds only.

Operational alerts should monitor application exit, repeated webhook 5xx,
database write errors, Discord rate limiting, and growing `error_logs` volume.

## Server management workflow

```text
/project create -> Discord resources -> database project/mappings -> success
/project archive -> move channels -> disable notifications
/project restore -> restore category -> enable notifications
/project delete -> confirmation -> delete resources -> cascade configuration
```

## Permissions

All `/project`, `/admin`, `/settings`, and `/test` commands require either
Administrator or Manage Server. `/review close` has the same restriction;
review participants may use approve, reject, and status inside registered threads.
Discord channel permissions still govern visibility and message/thread access.
