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
