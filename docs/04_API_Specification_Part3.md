# 04_API_Specification_Part3

# Discord API & Notification Specification

Project : CollabNotify
Version : 1.0
Status : Draft

---

# 1. 목적

본 문서는 Discord API 연동 방식, Embed UI 규격, 오류 처리, Retry 정책, Event Mapping, Sequence Flow 및 OpenAPI 예시를 정의한다.

GitHub, Jira, Confluence에서 전달된 이벤트는 모두 본 규격을 따라 Discord 메시지로 변환된다.

---

# 2. Discord API

## Discord Bot

Discord Bot은 `discord.py`를 사용하여 구현한다.

모든 메시지는 Bot 계정을 통해 전송한다.

---

## 전송 방식

지원

* Embed
* Button
* Role Mention
* Thread (향후 지원)
* File Attachment (향후 지원)

---

## Discord Gateway

Bot은 Gateway 연결을 유지하며 Webhook 이벤트는 HTTP Server(FastAPI)를 통해 수신한다.

```text
GitHub/Jira/Confluence
        │
        ▼
 FastAPI Webhook Server
        │
        ▼
 Discord Service
        │
        ▼
 Discord Bot
        │
        ▼
 Discord API
        │
        ▼
 Discord Channel
```

---

# 3. Discord Channel Mapping

기본 채널

| Channel     | 설명             |
| ----------- | -------------- |
| #jira       | Jira 이벤트       |
| #github     | GitHub 이벤트     |
| #confluence | Confluence 이벤트 |
| #notice     | 공지             |
| #deployment | 배포 및 CI/CD     |

확장 기능

* 프로젝트별 채널
* Repository별 채널
* 역할(Role)별 채널

---

# 4. Discord Embed 규격

모든 이벤트는 Embed 형태로 출력한다.

---

## 공통 규칙

| 항목          | 규칙                   |
| ----------- | -------------------- |
| Color       | 서비스별 고정              |
| Timestamp   | Discord Timestamp 사용 |
| Footer      | CollabNotify         |
| URL         | 원본 링크 포함             |
| Author      | 이벤트 수행자              |
| Fields      | 최대 25개               |
| Description | Markdown 지원          |

---

## Color

| 서비스        | Color  |
| ---------- | ------ |
| GitHub     | Purple |
| Jira       | Blue   |
| Confluence | Teal   |
| Success    | Green  |
| Warning    | Orange |
| Error      | Red    |

---

## Footer

```text
CollabNotify
```

또는

```text
CollabNotify • GitHub
```

---

## Timestamp

항상 표시한다.

Discord Native Timestamp 사용.

---

## Thumbnail

서비스 아이콘 표시

* GitHub Logo
* Jira Logo
* Confluence Logo

---

# 5. Embed Layout

```text
┌────────────────────────────────────────────┐
│ 🟣 Pull Request Opened                     │
│                                            │
│ Repository : CampusFlow                    │
│ PR         : #45                           │
│ Author     : 박지유                        │
│ Base       : main                          │
│ Head       : feature/login                 │
│ Status     : Open                          │
│                                            │
│ [Open Pull Request]                        │
│                                            │
│ CollabNotify • GitHub                      │
└────────────────────────────────────────────┘
```

---

# 6. Button 규격

지원

| Button            | 설명         |
| ----------------- | ---------- |
| Open Issue        | Jira       |
| Open Document     | Confluence |
| Open Pull Request | GitHub     |
| Open Commit       | GitHub     |
| Open Release      | GitHub     |

모든 버튼은 Link Button으로 구현한다.

---

# 7. Mention 규칙

지원

* User Mention
* Role Mention

예시

```text
Reviewer

@박지유
```

또는

```text
@Backend Team
```

---

# 8. Discord Service API

## send_embed()

설명

Embed 전송

입력

```python
channel_id
embed
view
```

반환

```python
discord.Message
```

---

## send_message()

설명

일반 메시지 전송

---

## edit_message()

설명

기존 Embed 수정

---

## delete_message()

설명

메시지 삭제

---

# 9. Embed Builder

서비스별 Builder를 제공한다.

```text
EmbedBuilder

├── build_jira()

├── build_github()

├── build_confluence()
```

반환

```python
discord.Embed
```

---

# 10. Error Code

## Common

| Code   | 의미                    |
| ------ | --------------------- |
| SYS001 | Internal Error        |
| SYS002 | Invalid Request       |
| SYS003 | Invalid Configuration |

---

## GitHub

| Code  | 의미                  |
| ----- | ------------------- |
| GH001 | Invalid Signature   |
| GH002 | Missing Header      |
| GH003 | Unsupported Event   |
| GH004 | Invalid Payload     |
| GH005 | Discord Send Failed |

---

## Jira

| Code  | 의미                  |
| ----- | ------------------- |
| JR001 | Invalid Payload     |
| JR002 | Missing Issue       |
| JR003 | Missing User        |
| JR004 | Unsupported Event   |
| JR005 | Discord Send Failed |

---

## Confluence

| Code  | 의미                  |
| ----- | ------------------- |
| CF001 | Invalid Payload     |
| CF002 | Missing Page        |
| CF003 | Missing User        |
| CF004 | Unsupported Event   |
| CF005 | Discord Send Failed |

---

## Discord

| Code  | 의미                |
| ----- | ----------------- |
| DC001 | Channel Not Found |
| DC002 | Permission Denied |
| DC003 | Invalid Embed     |
| DC004 | Rate Limited      |
| DC005 | API Timeout       |

---

# 11. Retry Policy

Retry 대상

* Discord API Timeout
* Discord Rate Limit
* Temporary Network Error

Retry 하지 않는 경우

* Invalid Payload
* Invalid Signature
* Unsupported Event
* Permission Error

---

## Retry 횟수

최대

```text
3회
```

---

## Retry 간격

```text
1초

↓

2초

↓

4초
```

Exponential Backoff 사용

---

## Retry Flow

```text
Discord API

↓

Fail

↓

Retry 1

↓

Retry 2

↓

Retry 3

↓

Error Log
```

---

# 12. Logging

INFO

```text
Webhook Received
```

```text
Discord Sent
```

WARNING

```text
Retry Started
```

ERROR

```text
Discord Send Failed
```

---

# 13. Event Mapping

## GitHub

| Event        | Embed          | Color       |
| ------------ | -------------- | ----------- |
| Issue        | Issue Embed    | Purple      |
| Pull Request | PR Embed       | Purple      |
| Push         | Push Embed     | Purple      |
| Review       | Review Embed   | Purple      |
| Release      | Release Embed  | Green       |
| Workflow     | Workflow Embed | Green / Red |

---

## Jira

| Event         | Embed          | Color  |
| ------------- | -------------- | ------ |
| Issue Created | Issue Embed    | Blue   |
| Updated       | Update Embed   | Blue   |
| Comment       | Comment Embed  | Blue   |
| Status        | Status Embed   | Blue   |
| Priority      | Priority Embed | Orange |

---

## Confluence

| Event        | Embed            | Color |
| ------------ | ---------------- | ----- |
| Page Created | Page Embed       | Teal  |
| Page Updated | Update Embed     | Teal  |
| Comment      | Comment Embed    | Teal  |
| Attachment   | Attachment Embed | Teal  |

---

# 14. Sequence Diagram

## GitHub Pull Request

```text
GitHub

↓

Webhook

↓

GitHub Router

↓

Signature Validator

↓

Dispatcher

↓

GithubHandler

↓

EmbedBuilder

↓

DiscordService

↓

Discord API

↓

Discord Channel
```

---

## Jira

```text
Jira

↓

Webhook

↓

Router

↓

Dispatcher

↓

JiraHandler

↓

EmbedBuilder

↓

DiscordService

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

Dispatcher

↓

ConfluenceHandler

↓

EmbedBuilder

↓

DiscordService

↓

Discord
```

---

# 15. Message Lifecycle

```text
Webhook

↓

Validate

↓

Dispatch

↓

Handler

↓

Embed Build

↓

Discord Send

↓

Success

↓

Log
```

실패 시

```text
Webhook

↓

Validate

↓

Handler

↓

Discord

↓

Retry

↓

Retry

↓

Retry

↓

Error Log
```

---

# 16. OpenAPI Specification

## GitHub

```http
POST /api/v1/webhook/github
```

Headers

```http
Content-Type: application/json
X-GitHub-Event: pull_request
X-Hub-Signature-256: sha256=...
```

Response

```json
{
  "success": true,
  "message": "GitHub webhook processed successfully."
}
```

---

## Jira

```http
POST /api/v1/webhook/jira
```

Headers

```http
Content-Type: application/json
```

Response

```json
{
  "success": true,
  "message": "Jira webhook processed successfully."
}
```

---

## Confluence

```http
POST /api/v1/webhook/confluence
```

Headers

```http
Content-Type: application/json
```

Response

```json
{
  "success": true,
  "message": "Confluence webhook processed successfully."
}
```

---

# 17. 성능 요구사항

| 항목               |          목표 |
| ---------------- | ----------: |
| Webhook 응답 시간    |       1초 이하 |
| Discord 전송 시작    |       3초 이하 |
| 평균 Embed 생성 시간   |    100ms 이하 |
| 최대 동시 Webhook 처리 | 100 req/sec |
| Discord API 재시도  |       최대 3회 |

---

# 18. 보안 요구사항

* 모든 Endpoint는 HTTPS를 사용한다.
* GitHub Webhook은 HMAC SHA-256 Signature를 검증한다.
* Jira/Confluence Endpoint는 랜덤 Webhook URL 또는 Reverse Proxy 인증을 사용한다.
* Bot Token 및 Secret은 `.env`에서 관리한다.
* 민감한 정보(Token, Secret)는 로그에 기록하지 않는다.

---

# 19. 구현 체크리스트

## Discord

* [ ] Discord Bot 연결
* [ ] Embed 생성
* [ ] Button 생성
* [ ] Role Mention
* [ ] Channel Mapping
* [ ] Timestamp 적용
* [ ] Footer 적용

## Event

* [ ] GitHub
* [ ] Jira
* [ ] Confluence

## Retry

* [ ] Exponential Backoff
* [ ] Error Log
* [ ] Retry Queue

## Logging

* [ ] INFO
* [ ] WARNING
* [ ] ERROR

---

# 20. 완료 기준

다음 조건을 모두 만족하면 API 구현이 완료된 것으로 판단한다.

* GitHub, Jira, Confluence Webhook을 정상 수신한다.
* 이벤트별 Handler가 올바르게 선택된다.
* Discord Embed가 규격에 맞게 생성된다.
* Link Button이 정상 동작한다.
* Retry 정책이 정상 수행된다.
* Error Code가 일관되게 반환된다.
* 모든 이벤트가 로그에 기록된다.
* 평균 처리 시간이 성능 요구사항을 만족한다.
