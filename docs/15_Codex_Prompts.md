# 15_Codex_Prompts.md

# CollabNotify Codex Development Prompts

Version: 1.0

---

# Purpose

This document contains standardized prompts for Codex to implement the CollabNotify project.

Each prompt should be executed sequentially.

Rules:

- Never redesign the architecture.
- Follow every document inside `/docs`.
- Preserve folder structure.
- Do not remove existing code.
- Do not simplify requirements.
- Generate production-quality code.
- Follow PEP8.
- Use Python type hints.
- Write clean, maintainable code.
- Add docstrings where appropriate.
- Add logging.
- Add error handling.
- Add unit tests whenever applicable.

The following documentation is authoritative.

- 01_Project_Overview.md
- 02_PRD.md
- 03_System_Architecture.md
- 04_API_Specification.md
- 05_Discord_UI_Guide.md
- 06_Database_Design.md
- 07_Project_Structure.md
- 08_Class_Design.md
- 09_Development_Guide.md
- 10_TODO.md
- 11_Deployment.md
- 12_Test_Cases.md
- 13_Future_Features.md
- 14_Implementation_Plan.md

Never contradict these documents.

---

# Prompt 01

## Initialize Project

Implement Phase 1 of the Implementation Plan.

Requirements:

- Create the project structure exactly as described.
- Initialize FastAPI.
- Configure Python package structure.
- Create requirements.txt.
- Configure logging.
- Configure environment variable loading.
- Create README if missing.
- Configure .gitignore.

Do not implement business logic.

Return:

- File tree
- Created files
- Explanation of architecture

---

# Prompt 02

## Discord Bot

Implement Phase 2.

Requirements:

- Create Discord Bot.
- Configure intents.
- Create NotificationService.
- Create ChannelService.
- Implement startup.
- Read token from environment variables.

Do not implement webhook logic.

Return complete source code.

---

# Prompt 03

## FastAPI Server

Implement Phase 3.

Requirements:

- Create FastAPI application.
- Configure routers.
- Configure Swagger.
- Implement Health Check.
- Configure middleware.
- Configure dependency injection.

Return complete source code.

---

# Prompt 04

## GitHub Webhook

Implement GitHub Webhook API.

Requirements:

Endpoint

POST /api/v1/webhook/github

Requirements

- Validate request
- Parse payload
- Call Dispatcher
- Return HTTP 200
- Add logging
- Handle exceptions

No Discord notification yet.

---

# Prompt 05

## Jira Webhook

Implement Jira Webhook API.

Requirements

POST /api/v1/webhook/jira

Validate payload.

Pass payload to Dispatcher.

Return HTTP 200.

---

# Prompt 06

## Confluence Webhook

Implement

POST /api/v1/webhook/confluence

Requirements identical to GitHub/Jira.

---

# Prompt 07

## Dispatcher

Implement EventDispatcher.

Requirements

- Register handlers.
- Route events.
- Unknown events must be logged.
- Raise meaningful exceptions.
- Unit tests included.

---

# Prompt 08

## GitHub Handler

Implement GithubHandler.

Requirements

Parse:

- Issue Opened
- Issue Closed
- Pull Request Opened
- Pull Request Merged
- Workflow Completed

Create NotificationModel.

Return model.

No Discord logic.

---

# Prompt 09

## Jira Handler

Implement JiraHandler.

Support

- Issue Created
- Issue Updated
- Issue Closed
- Comment Added

Return NotificationModel.

---

# Prompt 10

## Confluence Handler

Implement

ConfluenceHandler

Support

- Page Created
- Page Updated
- Comment Added
- Attachment Uploaded

Return NotificationModel.

---

# Prompt 11

## Embed Builder

Implement EmbedBuilder.

Requirements

Use

05_Discord_UI_Guide.md

Generate Discord embeds for

- GitHub
- Jira
- Confluence

Output

discord.Embed

---

# Prompt 12

## Notification Service

Implement NotificationService.

Responsibilities

- Send Embed
- Retry
- Exception handling
- Logging

---

# Prompt 13

## Database

Implement database.

Requirements

Use SQLAlchemy.

Create tables

- projects
- channel_mappings
- user_mappings
- role_mappings
- webhook_events
- notification_logs
- error_logs
- settings

Implement Repository pattern.

---

# Prompt 14

## Logging

Implement logging.

Requirements

Log

- startup
- webhook
- dispatcher
- handler
- database
- notification
- errors

Use rotating log files.

---

# Prompt 15

## Error Handling

Implement

- Global exception handler
- Validation handler
- Retry mechanism
- HTTP exceptions

---

# Prompt 16

## Docker

Implement deployment.

Requirements

Generate

- Dockerfile
- docker-compose.yml
- .env.example

Support

- FastAPI
- Discord Bot
- SQLite

---

# Prompt 17

## Testing

Implement all tests.

Requirements

Follow

12_Test_Cases.md

Create

- Unit Tests
- Integration Tests
- API Tests

Use pytest.

---

# Prompt 18

## Final Review

Perform a complete review.

Requirements

Check

- Architecture
- Folder structure
- Naming
- PEP8
- Type hints
- Logging
- Error handling
- Database
- Docker
- Tests

Fix every inconsistency automatically.

Return

- Summary
- Fixed files
- Remaining TODOs

---

# Prompt 19

## Production Readiness Review

Review the entire project as if preparing for open-source release.

Verify

- Security
- Performance
- Scalability
- Maintainability
- Documentation
- Docker deployment
- Code quality
- Test coverage

List every improvement needed before version 1.0.

Do not modify architecture.

---

# Prompt 20

## Final Deliverable

Generate the final production-ready version.

Requirements

- All documents satisfied.
- All implementation phases completed.
- No TODO comments.
- No placeholder code.
- No duplicated logic.
- All tests passing.
- Docker deployment successful.

Output

- Final project structure
- Build instructions
- Run instructions
- Test instructions
- Deployment instructions

The project should be ready for GitHub publication.