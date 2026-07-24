# 08_Class_Design

# Class Design Specification

Project : CollabNotify
Version : 1.0
Status : Draft

---

# 1. 목적

본 문서는 CollabNotify의 클래스 구조와 객체 간의 관계를 정의한다.

모든 클래스는 다음 원칙을 따른다.

* Single Responsibility Principle (SRP)
* Dependency Injection
* Layered Architecture
* Interface 기반 설계
* 높은 응집도
* 낮은 결합도

---

# 2. 클래스 다이어그램

```text
                         FastAPI Router
                               │
                               ▼
                     EventDispatcher
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
   GithubHandler         JiraHandler      ConfluenceHandler
          │                    │                    │
          └──────────────┬─────┴──────────────┬─────┘
                         ▼                    ▼
                NotificationService     EmbedBuilder
                         │                    │
                         └──────────┬─────────┘
                                    ▼
                            DiscordService
                                    │
                                    ▼
                              Discord API

```

---

# 3. Router Layer

## GithubRouter

### 역할

* GitHub Webhook 수신
* Signature 검증 요청
* Dispatcher 호출

### Method

```python
post_webhook()

health_check()
```

---

## JiraRouter

### Method

```python
post_webhook()
```

---

## ConfluenceRouter

### Method

```python
post_webhook()
```

---

# 4. EventDispatcher

## 책임

모든 이벤트를 분석하고 적절한 Handler를 선택한다.

---

### Properties

```python
handlers: dict
```

---

### Methods

```python
dispatch()

detect_service()

detect_event()

get_handler()
```

---

### 예시

```text
pull_request

↓

GithubPullRequestHandler
```

---

# 5. BaseHandler

모든 Handler의 부모 클래스

---

### Methods

```python
validate()

parse()

handle()

build_notification()
```

---

# 6. GithubHandler

Github 전용 Handler

---

### Methods

```python
handle_issue()

handle_pull_request()

handle_review()

handle_push()

handle_release()

handle_workflow()
```

---

### 내부 Flow

```text
Payload

↓

Parse

↓

Domain Event

↓

NotificationService
```

---

# 7. JiraHandler

### Methods

```python
handle_issue()

handle_comment()

handle_update()

handle_priority()

handle_status()
```

---

# 8. ConfluenceHandler

### Methods

```python
handle_page()

handle_comment()

handle_attachment()
```

---

# 9. NotificationService

## 책임

Notification 생성

Embed 생성 요청

Discord 전송 요청

로그 저장

---

### Methods

```python
send()

create_notification()

save_log()

retry()

mark_success()

mark_failed()
```

---

# 10. DiscordService

## 책임

Discord API 호출

---

### Methods

```python
send_embed()

send_message()

edit_message()

delete_message()

create_button()

mention_user()
```

---

### 반환

```python
discord.Message
```

---

# 11. EmbedBuilder

모든 Embed 생성 담당

---

### Methods

```python
build_github()

build_jira()

build_confluence()

build_error()

build_success()
```

---

### Private Methods

```python
_create_footer()

_create_author()

_create_timestamp()

_create_buttons()

_create_fields()
```

---

# 12. WebhookValidator

## 책임

Webhook 인증

---

### Methods

```python
validate_github()

validate_jira()

validate_confluence()
```

---

# 13. MappingService

## 책임

외부 사용자와 Discord 사용자 연결

---

### Methods

```python
find_user()

find_role()

find_channel()
```

---

# 14. ChannelService

## 책임

알맞은 Discord 채널 선택

---

### Methods

```python
get_channel()

get_default_channel()

resolve_project_channel()
```

---

# 15. LoggingService

## 책임

로그 기록

---

### Methods

```python
info()

warning()

error()

debug()

save_database_log()
```

---

# 16. RetryService

## 책임

재시도 처리

---

### Methods

```python
retry()

backoff()

schedule_retry()
```

---

# 17. StatisticsService

향후 지원

---

### Methods

```python
count_events()

daily_summary()

weekly_summary()

top_repository()
```

---

# 18. Repository Layer

## ProjectRepository

```python
create()

find_by_id()

find_by_name()

update()

delete()
```

---

## UserRepository

```python
find_discord_user()

save_mapping()

delete_mapping()
```

---

## NotificationRepository

```python
create()

update_status()

find_recent()

find_failed()
```

---

## ErrorRepository

```python
save()

find_all()

delete_old()
```

---

# 19. Domain Models

## GithubEvent

### Properties

```python
repository

action

author

title

url

created_at
```

---

## JiraEvent

### Properties

```python
project

issue

status

priority

assignee

url
```

---

## ConfluenceEvent

### Properties

```python
space

page

author

version

url
```

---

## Notification

### Properties

```python
title

description

fields

color

buttons

timestamp

footer
```

---

# 20. Database Models

## Project

```python
id

name

service

external_id

enabled
```

---

## ChannelMapping

```python
project_id

channel_id
```

---

## UserMapping

```python
external_username

discord_user
```

---

## NotificationLog

```python
event

status

message_id
```

---

## ErrorLog

```python
error_code

message

payload
```

---

# 21. 클래스 관계

```text
GithubHandler

↓

NotificationService

↓

EmbedBuilder

↓

DiscordService

↓

Discord API
```

Jira와 Confluence도 동일한 구조를 따른다.

---

# 22. Sequence

GitHub Pull Request

```text
GithubRouter

↓

Dispatcher

↓

GithubHandler

↓

NotificationService

↓

EmbedBuilder

↓

DiscordService

↓

Discord
```

---

# 23. 의존성 규칙

Router

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

역방향 참조는 금지한다.

---

# 24. Interface 설계

## IHandler

```python
validate()

parse()

handle()
```

---

## IRepository

```python
create()

update()

delete()

find()
```

---

## INotification

```python
send()

retry()

cancel()
```

---

# 25. Exception

## InvalidSignatureException

GitHub Signature 실패

---

## UnsupportedEventException

지원하지 않는 이벤트

---

## DiscordApiException

Discord API 실패

---

## ValidationException

Payload 오류

---

# 26. 향후 클래스

```text
SlackHandler

GitLabHandler

JenkinsHandler

AzureHandler

NotionHandler
```

Handler만 추가하면 기존 구조를 수정하지 않는다.

---

# 27. SOLID 적용

## S

모든 클래스는 하나의 책임만 가진다.

예

* EmbedBuilder → UI 생성만 담당
* DiscordService → Discord API 호출만 담당
* GithubHandler → GitHub 이벤트 처리만 담당

---

## O

새로운 서비스 추가 시 기존 코드 수정 없이 Handler를 추가하여 확장한다.

---

## L

BaseHandler를 상속한 모든 Handler는 동일한 방식으로 동작한다.

---

## I

작은 인터페이스를 사용한다.

예

```python
IHandler

IRepository

INotification
```

---

## D

상위 계층은 구현체가 아닌 인터페이스에 의존한다.

예

```text
NotificationService

↓

IDiscordService
```

---

# 28. 권장 클래스 수

| Layer      | 예상 클래스 수 |
| ---------- | -------: |
| Router     |        4 |
| Dispatcher |        1 |
| Handler    |    12~18 |
| Service    |     8~10 |
| Repository |        5 |
| Model      |        8 |
| Schema     |        8 |
| Utility    |        5 |

총 약 **50~60개의 클래스로 구성**된다.

---

# 29. 구현 순서

1. Domain Model
2. Repository
3. Service
4. EmbedBuilder
5. Handler
6. Dispatcher
7. Router
8. Discord Bot
9. Integration Test

---

# 30. 완료 기준

다음 조건을 만족하면 클래스 설계가 완료된 것으로 판단한다.

* 각 클래스의 책임이 명확하게 정의되어 있다.
* SOLID 원칙을 만족한다.
* Handler와 Service가 분리되어 있다.
* Repository Pattern을 적용한다.
* 인터페이스 기반 구조를 사용한다.
* 새로운 협업 도구를 최소한의 수정으로 추가할 수 있다.
* 의존성 방향이 일관되게 유지된다.
