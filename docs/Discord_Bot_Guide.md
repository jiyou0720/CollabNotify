# Discord Bot Guide

Create a bot in the Discord Developer Portal, invite it with `bot` and
`applications.commands` scopes, and grant View Channels, Manage Channels,
Send Messages, Create Public Threads, Send Messages in Threads, Manage Threads,
Embed Links, and Read Message History. Configure `DISCORD_TOKEN` and optionally
`DISCORD_GUILD_ID`; the latter enables fast guild-scoped command synchronization.

The client uses only the guild intent. It does not require message, privileged
message-content, member, or presence intents. Startup registers project, review, admin,
settings, and test command groups. Shutdown closes the Gateway client cleanly on
SIGINT/SIGTERM or application lifespan termination.

Never publish the bot token. Rotate it immediately if exposed. Keep bot roles
below channels/categories it must manage. User-facing command descriptions,
responses, embeds, buttons, checklists, errors, and thread messages are Korean;
class names, logs, schemas, and APIs remain English.
