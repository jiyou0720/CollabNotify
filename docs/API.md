# API

| Method | Path | Authentication | Result |
|---|---|---|---|
| GET | `/health` | None | Process liveness |
| POST | `/api/v1/webhook/github` | `X-Hub-Signature-256` HMAC-SHA256 | Accept GitHub event |
| POST | `/api/v1/webhook/jira` | `X-Webhook-Secret` | Accept Jira event |
| POST | `/api/v1/webhook/confluence` | `X-Webhook-Secret` | Accept Confluence event |

GitHub also requires `X-GitHub-Event`; its delivery ID is read from
`X-GitHub-Delivery`. Jira requires `webhookEvent` in the JSON body. Confluence
requires `eventType`. Jira and Confluence may provide `X-Request-ID` for
idempotency. Bodies must be JSON objects.

Successful supported deliveries return HTTP 200. Unsupported events return 202.
Repeated delivery IDs return 200 without redelivery. Invalid credentials return
401 and malformed input returns 400. Internal failures use the common safe error
response and are logged without exposing secrets. Interactive OpenAPI is served
at `/docs` when the application is running.

Webhook bodies are limited to 10 MiB while streaming, including chunked requests
without `Content-Length`. Production reverse proxies should enforce an equal or
smaller limit.

## Webhook project resolution

The public webhook paths and response schemas are unchanged. Each supported handler
extracts its provider identifier before delivery:

- GitHub: repository `full_name` (for example `organization/repository`)
- Jira: project `name`
- Confluence: space `name`

The identifier must exist in `project_aliases`. A missing alias does not change the
accepted webhook HTTP response and does not enqueue a Discord message; the application
records a warning containing only the provider and external identifier.

## Confluence event contract

`eventType` accepts `page_created`, `page_updated`, `comment_created`,
`attachment_created`, and `page_deleted`. Page events require a `page` object (native
webhooks may use `content`) containing a stable `id`. Comment and attachment events
also require `comment` or `attachment` respectively and must include the containing
page. Actor data may be supplied as `user`, `actor`, content `author`, `version.by`,
or `history.createdBy`; time may be supplied as `timestamp`, `occurredAt`, content
dates, or `version.when`.

Confluence Automation scalar aliases are also accepted: `author`, `editor`,
`displayName`, `version`, `createdAt`, `updatedAt`, `spaceName`, and `spaceKey`.
User objects accept `displayName`, `fullName`, and `publicName`. Native payloads may
provide scalar `page.version`, epoch-millisecond `creationDate`/`modificationDate`,
and account IDs. A supported non-empty value is always preferred over the Korean
unknown fallback.

Jira comment events accept either the native nested shape or Automation aliases
`issueKey`, `projectName`/`projectKey`, `issueUrl`, `commentAuthor`, and
`commentBody`. They always use the issue key to find an existing thread and set
`parent_delivery=false`; no comment event creates a parent Embed or thread.

Only `page_created` creates a Discord parent message and Thread. Every later event
uses the persisted Confluence Page ID in `review_threads.external_resource_id`.
`page_deleted` appends the deletion notice and archives the mapped Thread.
