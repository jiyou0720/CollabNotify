# CollabNotify Phase 13~14 Master Prompt

## ROLE

You are the lead software architect and senior backend engineer of the CollabNotify project.

The existing project (Phase 1~12) is COMPLETE.

Your job is to EXTEND the project.

### Core Rules

- Never remove existing functionality.
- Never redesign working architecture.
- Never break existing APIs.
- Preserve all tests.
- Extend using the existing architecture.
- All database changes must use Alembic migrations.
- No placeholder code.
- No TODO or FIXME.
- Production-quality code only.

---

# LOCALIZATION

This project targets Korean users.

## Discord UI MUST be Korean

This includes:

- Slash command descriptions
- Embed titles
- Embed descriptions
- Button labels
- Select menus
- Success messages
- Error messages
- Help messages
- Thread titles
- Review status
- Notification messages

Internal code, database schema, class names, APIs and documentation may remain in English.

---

# PHASE 13
## Discord Project Server Management

Implement administrator-only slash commands.

### /project create

Arguments

- project_name

Automatically create

Category

<Project Name>

Channels

- #general
- #github
- #jira
- #confluence
- #meeting
- #release

Store project in database.

Automatically create default mappings.

Return Korean success embed.

Example

프로젝트가 생성되었습니다.

### /project delete

Delete category, channels, mappings and related configuration.

Require confirmation.

### /project archive

Move category into

📦 Archived

Disable notifications.

### /project restore

Restore archived project.

### /project list

Display

- 프로젝트명
- 생성일
- 상태
- 연결된 채널

### /project info

Display

- 카테고리
- GitHub 채널
- Jira 채널
- Confluence 채널
- 웹훅 상태

### /project map

/project map CampusFlow github #github

### /project unmap

Remove mapping.

Permissions

Administrator or Manage Server only.

---

# PHASE 14
## Automatic Review Thread System

Every important collaboration event automatically creates a Discord Thread.

### GitHub

Create thread for

- Pull Request Opened
- Issue Opened
- Release Created
- Workflow Failed

Examples

🧵 PR #42 리뷰

🧵 Issue #103 토론

### Jira

Create thread for

- Issue Created
- Issue Updated
- Issue Assigned

Example

🧵 BUG-123 토론

### Confluence

Create thread for

- Page Created
- Page Updated
- Comment Added
- Attachment Added

Example

🧵 시스템 설계 리뷰

Thread behavior

Notification Message

↓

Automatically Create Thread

↓

Review Discussion

Automatically post

📋 리뷰 체크리스트

□ 내용을 확인했습니다.

□ 피드백을 작성했습니다.

□ 승인 또는 수정 요청을 남겨주세요.

Review status

🟡 검토 중

🟢 승인

🔄 수정 요청

🔴 반려

⚫ 완료

Automatically archive thread when

- PR Merged
- Issue Closed
- Jira Done
- Review Completed

Post

✅ 리뷰가 완료되어 스레드를 보관했습니다.

---

# DATABASE

Create or extend

- Projects
- ChannelMappings
- ReviewThreads
- ReviewerMappings
- ReviewStatus

---

# ADDITIONAL COMMANDS

/project create

/project delete

/project archive

/project restore

/project list

/project info

/project map

/project unmap

/review approve

/review reject

/review status

/review close

/admin sync

/admin cleanup

/admin status

/settings reviewers

/settings notifications

/settings archive-days

/settings auto-thread

/test github

/test jira

/test confluence

---

# IMPLEMENTATION RULES

Use

- FastAPI
- discord.py
- SQLAlchemy
- Alembic
- Dependency Injection
- Logging
- Type Hints

Write unit tests.

Update existing services instead of replacing them.

---

# DOCUMENTATION

Synchronize all documentation.

Update or create

- README.md
- Architecture.md
- API.md
- Database.md
- User_Guide.md
- Administrator_Guide.md
- Discord_Bot_Guide.md
- Installation.md
- Webhook_Guide.md
- Changelog.md

Include

- Updated architecture
- Folder structure
- Database schema
- ER Diagram (Markdown)
- Slash command reference
- Server management workflow
- Review workflow
- Thread lifecycle
- Webhook flow
- Discord workflow
- Permissions
- Environment variables
- Deployment guide
- Testing guide
- Example Discord messages
- Example review thread
- Future improvements

---

# QUALITY

Run

- pytest
- coverage
- ruff
- black
- isort
- pip check

Fix every issue until all tests pass.

---

# FINAL REVIEW

Review

- Architecture
- Database
- APIs
- Discord Bot
- Slash Commands
- Thread System
- Permissions
- Documentation

Remove

- Dead code
- Duplicate code
- Unused files
- Placeholder implementations

---

# FINAL REPORT

Provide

1. Files Created
2. Files Modified
3. Architecture Changes
4. Database Changes
5. Slash Commands
6. Server Management Workflow
7. Review Thread Workflow
8. Documentation Updated
9. Test Results
10. Coverage
11. Remaining Improvements
12. Production Readiness Score

Implementation is NOT complete until code, tests and documentation are fully synchronized.
