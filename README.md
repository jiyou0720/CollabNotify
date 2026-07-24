# CollabNotify

CollabNotify is a Python 3.12 service that authenticates GitHub, Jira, and
Confluence webhooks, routes them to project-specific Discord channels, and
creates persistent review threads for actionable events.

## Capabilities

- FastAPI webhook endpoints with HMAC/shared-secret verification and duplicate
  delivery protection.
- Korean Discord embeds and slash-command UI.
- `/project` lifecycle and channel mapping administration.
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
