# 03. System Architecture

# CollabNotify

> System Architecture Documentation

Version: 1.0
Status: Draft

---

# 1. 개요

CollabNotify는 Jira, Confluence, GitHub에서 발생하는 Webhook 이벤트를 수신하여 Discord Bot을 통해 실시간 알림을 제공하는 이벤트 기반(Event-Driven) 시스템이다.

각 협업 도구는 서로 독립적으로 동작하며, Dispatcher를 통해 공통 처리 파이프라인을 거쳐 Discord로 전달된다.

---

# 2. 전체 아키텍처

```text
                    +----------------+
                    |      Jira      |
                    +----------------+
                             |
                       HTTPS Webhook
                             |
                    +----------------+
                    |  FastAPI API   |
                    +----------------+
                             |
                             |
+----------------+           |           +----------------+
|  Confluence    |-----------+-----------|    GitHub      |
+----------------+                       +----------------+
            HTTPS Webhook                     HTTPS Webhook
                     \                         /
                      \                       /
                       ▼                     ▼

                +-------------------------+
                |     Event Dispatcher     |
                +-------------------------+
                           |
          +----------------+----------------+
          |                |                |
          ▼                ▼                ▼
   Jira Handler   Confluence Handler   GitHub Handler
          |                |                |
          +----------------+----------------+
                           |
                           ▼
                 Embed Builder Service
                           |
                           ▼
                 Discord Notification Service
                           |
                           ▼
                     Discord Bot API
                           |
                           ▼
                    Discord Server
```

---

# 3. 설계 원칙

## 단일 책임 원칙(SRP)

각 클래스는 하나의 역할만 담당한다.

예시

* JiraHandler → Jira 이벤트 처리
* GithubHandler → GitHub 이벤트 처리
* EmbedBuilder → Embed 생성
* DiscordService → Discord 전송

---

## 느슨한 결합(Loose Coupling)

각 서비스는 서로 직접 의존하지 않는다.

모든 이벤트는 Dispatcher를 통해 전달된다.

---

## 높은 응집도(High Cohesion)

관련 기능은 하나의 모듈 안에서 관리한다.

예시

```text
handlers/
    jira_handler.py
    github_handler.py
    confluence_handler.py
```

---

# 4. 프로젝트 구조

```text
collabnotify/

app/
│
├── main.py
├── config.py
│
├── routers/
│   ├── jira_router.py
│   ├── github_router.py
│   └── confluence_router.py
│
├── dispatcher/
│   └── dispatcher.py
│
├── handlers/
│   ├── jira_handler.py
│   ├── github_handler.py
│   └── confluence_handler.py
│
├── services/
│   ├── discord_service.py
│   ├── embed_builder.py
│   ├── webhook_validator.py
│   └── logger_service.py
│
├── models/
│
├── schemas/
│
├── utils/
│
├── bot/
│   └── bot.py
│
├── config/
│
└── tests/
```

---

# 5. 컴포넌트 역할

## Router Layer

역할

* Webhook 수신
* Request 검증
* Dispatcher 호출

비즈니스 로직은 포함하지 않는다.

---

## Dispatcher

역할

* 서비스 판별
* 이벤트 종류 판별
* 적절한 Handler 호출

예시

```text
GitHub
↓

Pull Request

↓

GithubHandler.handle_pull_request()
```

---

## Handler

역할

* Payload 해석
* 필요한 데이터 추출
* EmbedBuilder 호출

비즈니스 로직은 Handler에서 수행한다.

---

## Embed Builder

역할

Discord Embed를 생성한다.

모든 UI 생성은 여기에서 담당한다.

예시

* 제목
* 색상
* Footer
* Timestamp
* Field
* Button

---

## Discord Service

역할

* Discord API 호출
* 채널 조회
* Embed 전송
* 버튼 전송
* 오류 처리

---

## Logger Service

역할

* 이벤트 로그
* 오류 로그
* 재시도 로그

---

# 6. 이벤트 처리 흐름

## Jira

```text
Jira

↓

Webhook

↓

FastAPI Router

↓

Webhook Validator

↓

Dispatcher

↓

Jira Handler

↓

Embed Builder

↓

Discord Service

↓

Discord
```

---

## GitHub

```text
GitHub

↓

Webhook

↓

Router

↓

Validator

↓

Dispatcher

↓

Github Handler

↓

Embed Builder

↓

Discord
```

---

## Confluence

```text
Confluence

↓

Webhook

↓

Router

↓

Validator

↓

Dispatcher

↓

Confluence Handler

↓

Embed Builder

↓

Discord
```

---

# 7. 시퀀스 다이어그램

## Pull Request 생성

```text
GitHub
    |
    | Webhook
    ▼
FastAPI
    |
    ▼
Dispatcher
    |
    ▼
GithubHandler
    |
    ▼
EmbedBuilder
    |
    ▼
DiscordService
    |
    ▼
Discord API
    |
    ▼
Discord Channel
```

---

# 8. 계층 구조

```text
Presentation Layer

↓

Router Layer

↓

Dispatcher Layer

↓

Handler Layer

↓

Service Layer

↓

Infrastructure Layer

↓

Discord API
```

---

# 9. 의존성 구조

```text
Router

↓

Dispatcher

↓

Handler

↓

Service

↓

Discord API
```

상위 계층은 하위 계층만 참조한다.

역방향 의존성은 허용하지 않는다.

---

# 10. 예외 처리

## Router

* 잘못된 요청
* Secret 불일치
* JSON 오류

↓

HTTP 오류 반환

---

## Dispatcher

지원하지 않는 이벤트

↓

무시

↓

로그 기록

---

## Handler

Payload 누락

↓

예외 발생

↓

Logger 기록

---

## Discord

API 실패

↓

Retry

↓

실패 시 Error Log

---

# 11. 비동기 처리

모든 외부 통신은 async 기반으로 구현한다.

대상

* Discord API
* HTTP 요청
* Webhook 처리

FastAPI의 비동기 기능을 적극 활용한다.

---

# 12. 보안 구조

Webhook 요청마다 Secret을 검증한다.

지원

* GitHub Signature
* Jira Secret
* Confluence Secret

민감한 정보는 모두 환경 변수(.env)에서 관리한다.

절대로 소스 코드에 Token을 작성하지 않는다.

---

# 13. 로그 구조

로그 종류

* INFO
* WARNING
* ERROR

예시

```text
[INFO]

GitHub Pull Request Opened

Repository : CollabNotify

PR : #15
```

```text
[ERROR]

Discord Send Failed

Channel : github

Reason : Rate Limit
```

---

# 14. 확장 구조

새로운 협업 도구를 추가할 경우 다음 순서로 구현한다.

1. Router 추가
2. Handler 추가
3. Dispatcher 등록
4. EmbedBuilder 지원
5. DiscordService 호출

기존 코드는 수정하지 않고 새로운 모듈만 추가하도록 설계한다.

---

# 15. 향후 확장 아키텍처

```text
                Webhooks

      Jira
      GitHub
      Confluence
      GitLab
      Jenkins
      Azure DevOps
      Notion

             │
             ▼

      Event Dispatcher

             │
             ▼

      Handler Modules

             │
             ▼

      Embed Builder

             │
             ▼

      Discord Service

             │
             ▼

      Discord

             │
             ▼

      Dashboard
```

---

# 16. 설계 목표

본 시스템은 다음 목표를 만족하도록 설계한다.

* 높은 유지보수성
* 높은 확장성
* 낮은 결합도
* 높은 응집도
* 모듈화된 구조
* 이벤트 기반 처리
* 비동기 처리
* 안정적인 오류 처리
* 새로운 협업 도구의 손쉬운 추가
* Discord 중심의 통합 협업 알림 플랫폼 구축
