# 09_Development_Guide

# Development Guide

Project : CollabNotify
Version : 1.0
Status : Draft

---

# 1. 목적

본 문서는 CollabNotify 프로젝트의 개발 환경 구축, 실행 방법, 코딩 규칙 및 개발 절차를 정의한다.

새로운 개발자는 이 문서만으로 프로젝트를 실행하고 개발을 시작할 수 있어야 한다.

---

# 2. 개발 환경

## 운영체제

지원 환경

* Windows 11
* Ubuntu 22.04 LTS 이상
* macOS Sonoma 이상

---

## Python

권장 버전

```text
Python 3.12.x
```

확인

```bash
python --version
```

---

## Git

```bash
git --version
```

---

## Docker

권장

```text
Docker 27+
Docker Compose v2
```

---

## IDE

권장

* Visual Studio Code

추천 확장

* Python
* Pylance
* Ruff
* Black Formatter
* Docker
* GitLens

---

# 3. 프로젝트 설치

Repository Clone

```bash
git clone https://github.com/your-org/collabnotify.git
```

프로젝트 이동

```bash
cd collabnotify
```

---

# 4. 가상환경

Windows

```bash
python -m venv .venv
```

활성화

```bash
.venv\Scripts\activate
```

---

Linux / macOS

```bash
python3 -m venv .venv
```

활성화

```bash
source .venv/bin/activate
```

---

# 5. 패키지 설치

```bash
pip install -r requirements.txt
```

패키지 업데이트

```bash
pip freeze > requirements.txt
```

---

# 6. 프로젝트 구조

```text
app/
database/
tests/
docs/
logs/
scripts/
```

설명

| 폴더       | 설명        |
| -------- | --------- |
| app      | 애플리케이션 코드 |
| database | DB 관련 코드  |
| tests    | 테스트       |
| docs     | 문서        |
| logs     | 로그        |
| scripts  | 운영 스크립트   |

---

# 7. 환경 변수

`.env.example`

```env
# Discord
DISCORD_TOKEN=
DISCORD_GUILD_ID=

# GitHub
GITHUB_WEBHOOK_SECRET=

# Jira
JIRA_WEBHOOK_SECRET=

# Confluence
CONFLUENCE_WEBHOOK_SECRET=

# Database
DATABASE_URL=sqlite:///database/collabnotify.db

# Logging
LOG_LEVEL=INFO
```

실제 개발 시

```text
.env
```

파일을 생성하여 값을 입력한다.

---

# 8. 실행

FastAPI

```bash
uvicorn app.main:app --reload
```

또는

```bash
python -m uvicorn app.main:app --reload
```

기본 주소

```text
http://localhost:8000
```

Swagger

```text
http://localhost:8000/docs
```

OpenAPI JSON

```text
http://localhost:8000/openapi.json
```

---

# 9. Discord Bot 실행

```bash
python app/bot/bot.py
```

또는

```bash
python -m app.bot.bot
```

---

# 10. Docker 실행

Build

```bash
docker compose build
```

실행

```bash
docker compose up
```

백그라운드 실행

```bash
docker compose up -d
```

종료

```bash
docker compose down
```

---

# 11. Database 초기화

초기화

```bash
python scripts/init_db.py
```

Seed 데이터

```bash
python scripts/seed.py
```

---

# 12. 로그

로그 위치

```text
logs/
```

예시

```text
application.log

error.log
```

로그 레벨

* DEBUG
* INFO
* WARNING
* ERROR
* CRITICAL

---

# 13. 코드 스타일

Formatter

* Black

Linter

* Ruff

Import Sort

* isort

실행

```bash
black .
```

```bash
ruff check .
```

```bash
isort .
```

---

# 14. 네이밍 규칙

파일

```text
discord_service.py
```

클래스

```python
DiscordService
```

함수

```python
send_embed()
```

상수

```python
MAX_RETRY
```

변수

```python
channel_id
```

---

# 15. 브랜치 전략

메인 브랜치

```text
main
```

개발 브랜치

```text
develop
```

기능 브랜치

```text
feature/github-handler
```

버그 수정

```text
fix/embed-error
```

문서

```text
docs/api
```

---

# 16. Commit Convention

형식

```text
type(scope): message
```

예시

```text
feat(github): add pull request webhook
```

```text
fix(discord): resolve embed color bug
```

```text
docs(api): update webhook specification
```

Commit Type

* feat
* fix
* refactor
* docs
* style
* test
* chore

---

# 17. 개발 순서

1.

프로젝트 Clone

↓

2.

환경 변수 설정

↓

3.

패키지 설치

↓

4.

Database 생성

↓

5.

Discord Bot 실행

↓

6.

FastAPI 실행

↓

7.

Webhook 테스트

↓

8.

Discord 확인

---

# 18. 테스트

전체 테스트

```bash
pytest
```

특정 테스트

```bash
pytest tests/services
```

Coverage

```bash
pytest --cov=app
```

---

# 19. API 테스트

Swagger

```text
http://localhost:8000/docs
```

Webhook 테스트

예시

```bash
curl -X POST http://localhost:8000/api/v1/webhook/github
```

또는

* Postman
* Insomnia

---

# 20. 개발 체크리스트

환경

* [ ] Python 설치
* [ ] Git 설치
* [ ] Docker 설치

프로젝트

* [ ] Clone
* [ ] Virtual Environment
* [ ] Requirements 설치

설정

* [ ] .env 생성
* [ ] Discord Token 입력
* [ ] Database 생성

실행

* [ ] FastAPI 실행
* [ ] Discord Bot 실행

테스트

* [ ] GitHub Webhook
* [ ] Jira Webhook
* [ ] Confluence Webhook

---

# 21. 문제 해결

## ModuleNotFoundError

원인

패키지 미설치

해결

```bash
pip install -r requirements.txt
```

---

## Discord Bot Login 실패

원인

잘못된 Token

확인

```text
DISCORD_TOKEN
```

---

## Webhook 401

원인

Signature 불일치

확인

* Secret
* Header
* Payload

---

## Database Error

확인

```text
DATABASE_URL
```

DB 초기화

```bash
python scripts/init_db.py
```

---

# 22. 배포 전 확인

* [ ] 모든 테스트 통과
* [ ] Black 적용
* [ ] Ruff 경고 없음
* [ ] .env 제외 확인
* [ ] 로그 정리
* [ ] Secret 노출 여부 확인

---

# 23. Git Ignore

```text
.venv/
__pycache__/
.pytest_cache/
.env
logs/
*.pyc
*.db
.coverage
htmlcov/
.vscode/
.idea/
```

---

# 24. 개발 원칙

* 함수는 하나의 책임만 가진다.
* Handler는 Payload 처리만 담당한다.
* Service는 비즈니스 로직만 담당한다.
* Repository만 Database에 접근한다.
* 모든 외부 통신은 예외 처리를 구현한다.
* 환경 변수는 코드에 하드코딩하지 않는다.
* 테스트 가능한 구조를 유지한다.

---

# 25. 완료 기준

다음 조건을 만족하면 개발 환경 구성이 완료된 것으로 판단한다.

* 프로젝트가 정상적으로 실행된다.
* Discord Bot이 연결된다.
* FastAPI가 정상적으로 실행된다.
* 데이터베이스가 초기화된다.
* GitHub, Jira, Confluence Webhook을 수신할 수 있다.
* 테스트가 정상적으로 실행된다.
* 코드 스타일 검사와 포맷팅을 통과한다.
