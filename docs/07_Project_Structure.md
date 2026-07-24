# 07_Project_Structure

# Project Structure & Source Code Organization

Project : CollabNotify
Version : 1.0
Status : Draft

---

# 1. 목적

본 문서는 CollabNotify 프로젝트의 디렉터리 구조와 각 모듈의 역할을 정의한다.

프로젝트는 다음 원칙을 따른다.

* 계층형(Layered Architecture)
* 모듈화(Modular Design)
* 단일 책임 원칙(SRP)
* 의존성 최소화
* 높은 확장성

---

# 2. 전체 프로젝트 구조

```text
collabnotify/
│
├── app/
│   ├── api/
│   ├── bot/
│   ├── config/
│   ├── core/
│   ├── dispatcher/
│   ├── handlers/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   ├── workers/
│   └── main.py
│
├── docs/
│
├── tests/
│
├── scripts/
│
├── logs/
│
├── database/
│
├── .env
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── README.md
└── LICENSE
```

---

# 3. app/

모든 애플리케이션 소스코드를 포함한다.

```text
app/
```

---

# 4. api/

Webhook Endpoint를 관리한다.

```text
api/
├── github.py
├── jira.py
├── confluence.py
└── health.py
```

역할

* HTTP 요청 수신
* Header 확인
* Signature 검증 요청
* Dispatcher 호출
* Response 반환

비즈니스 로직은 포함하지 않는다.

---

# 5. bot/

Discord Bot을 관리한다.

```text
bot/
├── bot.py
├── commands.py
├── events.py
└── views.py
```

### bot.py

Bot 생성

Gateway 연결

Lifecycle 관리

---

### commands.py

Slash Command

(향후 지원)

---

### events.py

Discord 이벤트 처리

예

* on_ready
* on_message

---

### views.py

Discord Button

Discord View

Persistent View

---

# 6. config/

환경설정

```text
config/
├── settings.py
├── logging.py
└── constants.py
```

---

### settings.py

* .env 로드
* Token 관리
* DB URL
* Secret 관리

---

### logging.py

Logging 설정

---

### constants.py

상수

예

```python
MAX_RETRY = 3
```

---

# 7. core/

공통 핵심 기능

```text
core/
├── exceptions.py
├── security.py
├── retry.py
└── enums.py
```

---

### exceptions.py

프로젝트 전용 Exception

예

```python
InvalidSignatureError
```

---

### security.py

* GitHub Signature 검증
* Jira 인증 검증
* Secret 관리

---

### retry.py

Exponential Backoff

Retry 정책

---

### enums.py

모든 Enum 정의

예

* EventType
* ServiceType
* LogLevel

---

# 8. dispatcher/

```text
dispatcher/
└── dispatcher.py
```

역할

* 이벤트 종류 판별
* Handler 선택
* Handler 실행

예

```text
GitHub

↓

pull_request

↓

GithubPullRequestHandler
```

---

# 9. handlers/

서비스별 이벤트 처리

```text
handlers/

├── github/
│   ├── issue.py
│   ├── pull_request.py
│   ├── review.py
│   ├── push.py
│   ├── workflow.py
│   ├── release.py
│   ├── create.py
│   └── delete.py
│
├── jira/
│   ├── issue.py
│   ├── comment.py
│   └── update.py
│
├── confluence/
│   ├── page.py
│   ├── comment.py
│   └── attachment.py
│
└── base_handler.py
```

역할

* Payload 분석
* Domain 객체 생성
* Service 호출

---

# 10. models/

SQLAlchemy Model

```text
models/
├── project.py
├── channel.py
├── user_mapping.py
├── notification.py
├── error_log.py
└── setting.py
```

역할

DB Entity 정의

---

# 11. repositories/

Database 접근 계층

```text
repositories/
├── project_repository.py
├── notification_repository.py
├── channel_repository.py
├── user_repository.py
└── error_repository.py
```

Repository Pattern 적용

역할

* CRUD
* Query
* Transaction

---

# 12. schemas/

Pydantic Schema

```text
schemas/

├── github.py
├── jira.py
├── confluence.py
├── response.py
└── common.py
```

역할

* Request Validation
* Response Validation

---

# 13. services/

비즈니스 로직

```text
services/

├── discord_service.py
├── embed_builder.py
├── notification_service.py
├── logging_service.py
├── channel_service.py
├── mapping_service.py
├── webhook_service.py
└── statistics_service.py
```

---

### discord_service.py

* Embed 전송
* Message 수정
* 삭제

---

### embed_builder.py

모든 Embed 생성

---

### notification_service.py

Notification 생성

로그 저장

---

### channel_service.py

Discord 채널 선택

---

### mapping_service.py

User Mapping

Role Mapping

---

### webhook_service.py

Webhook 처리

---

### statistics_service.py

알림 통계

(향후)

---

# 14. utils/

공통 함수

```text
utils/

├── datetime.py
├── markdown.py
├── formatter.py
├── validator.py
└── helpers.py
```

예

시간 변환

Markdown Escape

URL 처리

---

# 15. workers/

비동기 작업

```text
workers/

├── retry_worker.py
├── cleanup_worker.py
└── scheduler.py
```

역할

Retry

Log 정리

백그라운드 작업

---

# 16. database/

```text
database/

├── database.py
├── session.py
└── migrations/
```

database.py

Engine 생성

session.py

Session 관리

---

# 17. tests/

```text
tests/

├── api/
├── handlers/
├── services/
├── repositories/
├── integration/
└── fixtures/
```

---

### api/

API 테스트

---

### handlers/

Handler 테스트

---

### services/

Service 테스트

---

### integration/

통합 테스트

---

# 18. scripts/

운영 스크립트

```text
scripts/

init_db.py

seed.py

backup.py
```

---

# 19. logs/

로그 저장

```text
logs/

application.log

error.log
```

Git에 포함하지 않는다.

---

# 20. 의존성 구조

```text
API

↓

Dispatcher

↓

Handler

↓

Service

↓

Repository

↓

Database
```

상위 계층은 하위 계층만 참조한다.

Repository는 Service를 참조하지 않는다.

Handler는 Database를 직접 접근하지 않는다.

---

# 21. 개발 규칙

## 파일명

snake_case

예

```text
discord_service.py
```

---

## 클래스명

PascalCase

```python
DiscordService
```

---

## 함수명

snake_case

```python
send_embed()
```

---

## 상수

UPPER_CASE

```python
MAX_RETRY
```

---

# 22. Import 규칙

순서

1. Standard Library
2. Third-party
3. Local Module

예

```python
import json

from fastapi import APIRouter

from app.services.discord_service import DiscordService
```

---

# 23. 신규 서비스 추가 절차

예를 들어 GitLab을 추가하는 경우

1.

```text
api/gitlab.py
```

2.

```text
handlers/gitlab/
```

3.

```text
schemas/gitlab.py
```

4.

```text
services/gitlab_service.py
```

5.

Dispatcher 등록

6.

EmbedBuilder 추가

기존 GitHub 코드 수정 없이 확장 가능해야 한다.

---

# 24. 최종 구조 요약

```text
API Layer
        │
        ▼
Dispatcher
        │
        ▼
Handlers
        │
        ▼
Services
        │
        ▼
Repositories
        │
        ▼
Database
        │
        ▼
Discord API
```

---

# 25. 완료 기준

다음 조건을 만족하면 프로젝트 구조 설계가 완료된 것으로 판단한다.

* 계층별 책임이 명확하게 분리되어 있다.
* 서비스 추가 시 기존 코드 수정이 최소화된다.
* Handler와 Service의 역할이 분리되어 있다.
* Repository Pattern을 적용하여 데이터 접근을 캡슐화한다.
* 테스트 코드 구조가 실제 프로젝트 구조와 일치한다.
* 유지보수성과 확장성을 고려한 디렉터리 구조를 제공한다.
