# CollabNotify

CollabNotify is a Python 3.12 service that authenticates GitHub, Jira, and
Confluence webhooks, routes them to project-specific Discord channels, and
creates persistent review threads for actionable events.

## Capabilities

- FastAPI webhook endpoints with HMAC/shared-secret verification and duplicate
  delivery protection.
- Korean Discord embeds and slash-command UI.
- `/project` lifecycle and external provider alias administration.
- Automatic review threads, checklists, five review states, and completion
  archiving.
- Persistent SQLite/SQLAlchemy state managed exclusively by Alembic.
- Structured logging, retries, health checks, Docker deployment, and tests.

## Quick start

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On Windows, activate with `.venv\Scripts\Activate.ps1` and copy the environment
file with `Copy-Item .env.example .env`. Configure every secret before startup.
The Discord Gateway starts with the API when `ENABLE_DISCORD_BOT=true`.

Docker deployment:

```bash
docker compose up --build -d
docker compose logs -f collabnotify
```

Compose stores SQLite data and rotating log files in Docker-managed
`runtime_data` and `runtime_logs` volumes. It deliberately does not mount over
the application `database/` package, so Alembic migrations remain available.

## Verification

```bash
python -m pytest --cov=app --cov=database --cov-report=term-missing
python -m black --check .
python -m isort --check-only .
python -m ruff check .
python -m pip check
```

See [Installation](docs/Installation.md), [User Guide](docs/User_Guide.md),
[Administrator Guide](docs/Administrator_Guide.md), and
[Webhook Guide](docs/Webhook_Guide.md) for complete operation instructions.

---

## 기본 설정 및 실행 방법

아래 절차는 Windows PowerShell과 Docker Desktop을 기준으로 한다.

### 1. 사전 준비

다음 프로그램을 설치하고 실행 상태를 확인한다.

- Git
- Docker Desktop
- Python 3.12 — Docker만 사용할 경우 선택 사항

```powershell
docker version
git --version
```

### 2. Discord Bot 기본 설정

1. Discord Developer Portal에서 Application과 Bot을 생성한다.
2. Bot Token을 발급한다.
3. OAuth2 URL Generator에서 `bot`, `applications.commands` scope를 선택한다.
4. 봇에 다음 권한을 부여하고 테스트 서버에 추가한다.

- 채널 보기
- 채널 관리
- 메시지 보내기
- 공개 스레드 만들기
- 스레드에서 메시지 보내기
- 스레드 관리
- 메시지 기록 보기
- 링크 첨부
- 애플리케이션 명령 사용

테스트 서버에서 봇 역할은 봇이 관리할 채널보다 역할 목록의 위쪽에
배치한다. Message Content, Members, Presence 같은 privileged intent는 필요하지
않다.

### 3. 환경 변수 설정

프로젝트 루트에서 예제 파일을 복사한다.

```powershell
Set-Location F:\ma
Copy-Item .env.example .env
```

`.env`에 실제 값을 입력한다.

```env
DISCORD_TOKEN=발급받은_봇_토큰
DISCORD_GUILD_ID=테스트_서버_ID
ENABLE_DISCORD_BOT=true

GITHUB_WEBHOOK_SECRET=충분히_긴_GitHub_시크릿
JIRA_WEBHOOK_SECRET=충분히_긴_Jira_시크릿
CONFLUENCE_WEBHOOK_SECRET=충분히_긴_Confluence_시크릿

DATABASE_URL=sqlite:///database/collabnotify.db
DOCKER_DATABASE_URL=sqlite:////app/data/collabnotify.db
LOG_LEVEL=INFO
```

값과 같은 줄에 주석을 작성하지 않는다. 특히 서버 ID는 다음과 같이 숫자만
입력해야 한다.

```env
# Discord 테스트 서버 ID
DISCORD_GUILD_ID=123456789012345678
```

`.env`에는 실제 비밀값이 들어 있으므로 Git에 커밋하지 않는다. 프로젝트의
`.gitignore`와 `.dockerignore`에서 이 파일을 제외한다.

### 4. Docker로 실행

프로젝트 루트에서 다음 명령을 실행한다.

```powershell
docker compose up --build -d
```

컨테이너 상태를 확인한다.

```powershell
docker compose ps
```

정상 상태는 다음과 같다.

```text
Up ... (healthy)
```

시작 로그를 확인한다.

```powershell
docker compose logs --tail 100 collabnotify
```

정상 시작 시 Alembic migration, Discord Gateway 연결,
`Discord client is ready`, `Application startup complete` 로그가 출력된다.
음성 기능과 관련된
PyNaCl 또는 davey 경고는 이 프로젝트에서 음성 기능을 사용하지 않으므로
무시할 수 있다.

### 5. API 상태 확인

```powershell
Invoke-RestMethod http://localhost:8000/health
```

정상 응답:

```json
{"status":"ok"}
```

Swagger API 문서는 브라우저에서 확인한다.

```text
http://localhost:8000/docs
```

### 6. Discord 최초 설정

테스트 서버에서 관리자 또는 서버 관리 권한이 있는 계정으로 다음 명령을
순서대로 실행한다.

```text
/admin sync
/admin status
/project create
```

`/project create`의 `project_name`에는 실제 프로젝트명을 입력한다. 명령은
프로젝트 카테고리와 다음 채널을 자동 생성한다.

```text
#general
#github
#jira
#confluence
#meeting
#release
```

생성된 설정을 확인한다.

```text
/project list
/project info
```

### 7. Discord 알림 테스트

```text
/test github
/test jira
/test confluence
```

자동 리뷰 스레드와 프로젝트 알림을 활성화한다.

```text
/settings auto-thread enabled:True
/settings archive-days days:1
/settings notifications project_name:프로젝트명 enabled:True
```

필요하면 프로젝트 리뷰어를 등록한다.

```text
/settings reviewers project_name:프로젝트명 action:추가 user:@사용자
```

### 8. 외부 웹훅 연결

GitHub, Jira, Confluence가 접근할 수 있는 공개 HTTPS 주소가 필요하다. 로컬
환경에서는 HTTPS tunnel을 사용한다.

```text
GitHub:     https://공개주소/api/v1/webhook/github
Jira:       https://공개주소/api/v1/webhook/jira
Confluence: https://공개주소/api/v1/webhook/confluence
```

각 서비스의 웹훅 secret은 `.env`의 대응 값과 동일해야 한다. GitHub는
`X-Hub-Signature-256` HMAC 서명을 사용하고 Jira와 Confluence는
`X-Webhook-Secret` 헤더를 사용한다.

### 9. 재시작 및 종료

재시작:

```powershell
docker compose restart collabnotify
```

코드 또는 Docker 설정 변경 후 재빌드:

```powershell
docker compose up --build -d
```

종료:

```powershell
docker compose down
```

SQLite 데이터와 로그는 Docker의 `runtime_data`, `runtime_logs` volume에
보존된다. 다음 명령은 volume까지 삭제하므로 데이터 초기화가 목적이 아니라면
사용하지 않는다.

```powershell
docker compose down -v
```

### 10. Python 3.12로 직접 실행

Docker를 사용하지 않을 경우 다음 순서로 실행한다.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Discord Bot만 단독 실행하려면 다음 명령을 사용한다.

```powershell
python -m app.main
```
## 외부 프로젝트 별칭 연결

CollabNotify의 Discord 프로젝트명은 GitHub 저장소명, Jira 프로젝트명 또는
Confluence 공간명과 같을 필요가 없습니다. Discord에서 서버 관리자 권한으로 다음
명령을 실행해 외부 식별자를 내부 프로젝트에 연결합니다.

```text
/project alias add provider:GitHub external_name:organization/repository project_name:내부 프로젝트명
/project alias add provider:Jira external_name:CollabNotify project_name:내부 프로젝트명
/project alias add provider:Confluence external_name:Development project_name:내부 프로젝트명
/project alias list
```

별칭을 삭제하려면
`/project alias remove provider:<서비스> external_name:<외부 식별자>`를 실행합니다.
GitHub의 외부 이름은 대소문자 구분 없이 저장·조회되며, Jira와 Confluence는 실제
웹훅 payload의 이름을 그대로 입력해야 합니다. 별칭이 없는 웹훅은 HTTP 요청을
실패시키지 않고 경고 로그만 남긴 뒤 Discord 전송을 건너뜁니다.

## Jira Activity Timeline

Jira 이슈 생성 시 만들어진 리뷰 스레드는 해당 이슈의 전체 활동 기록으로
사용됩니다. 이후 이슈의 상태, 담당자, 우선순위, 제목, 설명, 라벨, 해결 상태 변경과
댓글 생성·수정·삭제가 이슈 키로 조회된 동일 스레드에 한국어 메시지로 추가됩니다.
새 스레드는 이슈 생성 이벤트에서만 만들며, 매핑된 스레드가 없으면 경고 로그를
남기고 활동을 건너뜁니다.

상태가 `Done`, `Closed` 또는 `완료`가 되면 완료 메시지를 게시하고 스레드를
보관합니다. 완료 상태에서 다른 상태로 변경되면 기존 스레드를 자동으로 다시 열고
작업 재개 메시지를 게시합니다. Jira Automation은 중복 전송 방지를 위해 각 요청에
고유한 `X-Request-ID` 헤더를 포함해야 합니다.

## GitHub PR Activity Timeline

Pull Request가 열릴 때 생성된 리뷰 스레드는 해당 PR의 단일 협업 공간으로 계속
사용됩니다. PR 편집, 새 commit push, 리뷰 요청, 리뷰 결과, 리뷰 댓글, 일반 댓글,
라벨·담당자·Draft 상태 변경을 모두 같은 스레드에 한국어 메시지로 기록합니다.
`synchronize`는 commit마다 메시지를 보내지 않고 commit 수, 짧은 SHA, 작성자와
commit 메시지 첫 줄을 하나의 요약 메시지로 게시합니다.

PR이 merge되지 않은 채 종료되면 기존 부모 embed를 `🔒 PR 종료`, merge되면
`✅ PR 병합` 상태로 수정한 뒤 기존 스레드를 보관합니다. PR을 다시 열면 동일
스레드의 보관을 해제하고 `♻️ PR가 다시 열렸습니다.`를 게시합니다. GitHub의
`X-GitHub-Delivery`가 중복 webhook의 타임라인 재게시를 방지합니다.

## 통합 Thread Lifecycle

GitHub PR, Jira Issue, Confluence Page는 모두 다음 정책을 사용합니다.

```text
최초 생성 → 부모 embed 1개 + Discord thread 1개
상태 변경 → 기존 부모 embed 수정
활동 발생 → 기존 thread에만 추가
완료       → 부모 embed 수정 + thread 완료 기록 + 보관
재개       → 기존 thread 복원
```

댓글·push·첨부파일 같은 활동은 부모 채널에 새 메시지를 만들지 않습니다. 과거
버전에서 생성되어 부모 메시지를 찾을 수 없는 thread는 경고를 남기되 timeline
기록을 계속 처리합니다.

## Confluence 문서 타임라인

`page_created`는 `#confluence` 채널에 스페이스·제목·작성자·생성 시각·버전·문서
링크를 포함한 Teal Embed를 게시하고 Thread 하나를 만듭니다. Page ID와 부모 메시지
ID, Thread ID는 `review_threads`에 저장됩니다. 이후 `page_updated`,
`comment_created`, `attachment_created`는 새 부모 메시지나 Thread를 만들지 않고
Page ID로 기존 Thread를 찾아 활동을 누적합니다. `page_deleted`는
`🗑 문서가 삭제되었습니다.`를 게시한 후 같은 Thread를 자동 보관합니다.

Confluence Automation 요청은 [Webhook Guide](docs/Webhook_Guide.md)의 JSON 예시처럼
`eventType`, `page.id`, `space.name`, 사용자, 시각과 버전을 명시적으로 전달해야
합니다. 후속 이벤트에 Page ID가 빠지면 기존 Thread를 찾을 수 없습니다.

GitHub, Jira, Confluence의 Thread 생성·조회·게시·보관은 공통 `ThreadManager`
인터페이스와 `ReviewThreadService` 구현을 사용합니다. 새 provider는 webhook을
`Notification`으로 정규화하고 동일한 lifecycle 메타데이터만 제공하면 이 구조를
재사용할 수 있습니다.

## Confluence Cloud 문서 리뷰 워크플로우

신규 문서(`page_created`)가 Discord에 전달되면 리뷰 스레드에 다음 영구 버튼이
생성됩니다.

- 일반 문서(1명) / 전체 팀 문서(3명) 승인 기준 설정
- 리뷰 완료 및 Confluence 감사 댓글
- 수정 요청 모달, 요청 취소, 요청자의 수정 확인 완료
- `page_updated` 감지 후 요청자 스레드 멘션
- 리뷰 및 수정 요청 리마인더
- 기준 충족 및 열린 수정 요청 0건일 때 `approved` 라벨과
  `collabnotify.review` content property 기록

Confluence Cloud 양방향 쓰기를 위해 아래 환경 변수가 필요합니다.

```env
CONFLUENCE_BASE_URL=https://jehye.atlassian.net
CONFLUENCE_EMAIL=atlassian-account@example.com
CONFLUENCE_API_TOKEN=your-atlassian-api-token
REVIEW_REMINDER_HOURS=48
CHANGE_REQUEST_REMINDER_HOURS=48
```

Atlassian Automation webhook 주소:

```text
https://<cloudflared-public-host>/api/v1/webhook/confluence
```

요청 헤더에는 `X-Webhook-Secret: <CONFLUENCE_WEBHOOK_SECRET>`가 필요합니다.
로컬 서버는 `uvicorn app.main:app --host 0.0.0.0 --port 8000`으로 실행합니다.
