# Webhook Guide

Public base URL examples:

- GitHub: `https://notify.example.com/api/v1/webhook/github`
- Jira: `https://notify.example.com/api/v1/webhook/jira`
- Confluence: `https://notify.example.com/api/v1/webhook/confluence`

Set GitHub content type to JSON and use the same secret as
`GITHUB_WEBHOOK_SECRET`; the server validates the exact raw body with
`X-Hub-Signature-256`. Configure Jira and Confluence to send the secret in
`X-Webhook-Secret`. Their values must match the corresponding environment
variables. Always use HTTPS.

Supported review-opening families are GitHub issue opened, pull request opened,
release created, failed workflow; Jira issue created/updated/assigned; and
Confluence page created/updated, comment added, attachment added. GitHub merged
or closed resources and Jira Done/Closed events complete matching review threads.

Use unique delivery/request IDs. A 202 means the authenticated event is not
handled; a repeated ID is acknowledged without duplicate delivery. For 401,
check the selected secret and proxy body/header preservation. For 400, verify
JSON object shape and required event field/header. For 5xx, correlate structured
logs and `error_logs`; provider retries are safe when IDs remain stable.

```text
Provider -> HTTPS endpoint -> authenticate -> deduplicate -> normalize event
         -> resolve project/channel -> Korean Discord embed -> optional thread
```
