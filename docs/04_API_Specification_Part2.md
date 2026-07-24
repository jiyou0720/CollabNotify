# 04_API_Specification_Part2

# Jira & Confluence Webhook Specification

Project : CollabNotify
Version : 1.0
Status : Draft

---

# 1. 목적

본 문서는 Jira Cloud 및 Confluence Cloud에서 발생하는 Webhook 이벤트를 수신하고 Discord 알림으로 변환하기 위한 API 명세를 정의한다.

모든 Webhook은 HTTPS POST 요청으로 전달되며 JSON Payload를 사용한다.

---

# 2. Endpoint

## Jira

```http
POST /api/v1/webhook/jira
```

설명

Jira Cloud Webhook 수신 Endpoint

---

## Confluence

```http
POST /api/v1/webhook/confluence
```

설명

Confluence Cloud Webhook 수신 Endpoint

---

# 3. 공통 Header

| Header       | Required | 설명                |
| ------------ | -------- | ----------------- |
| Content-Type | Yes      | application/json  |
| User-Agent   | Yes      | Atlassian Webhook |
| X-Request-ID | No       | 요청 추적용            |

---

# 4. 인증

Webhook Endpoint는 외부에 공개되므로 인증이 필요하다.

권장 방식

* HTTPS 사용
* 충분히 긴 랜덤 Webhook URL 사용
* Reverse Proxy(IP 제한 가능)
* 요청 Origin 검증
* 선택적으로 Reverse Proxy에서 Secret Header 추가

민감한 설정은 `.env`에서 관리한다.

---

# 5. 공통 응답

성공

```http
200 OK
```

```json
{
  "success": true,
  "message": "Webhook processed successfully."
}
```

---

잘못된 요청

```http
400 Bad Request
```

```json
{
  "success": false,
  "error": "Invalid payload."
}
```

---

인증 실패

```http
401 Unauthorized
```

```json
{
  "success": false,
  "error": "Unauthorized."
}
```

---

지원하지 않는 이벤트

```http
202 Accepted
```

```json
{
  "success": true,
  "message": "Ignored event."
}
```

---

# 6. Jira Event 목록

지원 이벤트

| Event              | 지원 |
| ------------------ | -- |
| jira:issue_created | O  |
| jira:issue_updated | O  |
| jira:issue_deleted | O  |
| comment_created    | O  |
| comment_updated    | O  |
| comment_deleted    | O  |

---

# 7. Jira Payload

대표 구조

```json
{
  "timestamp": 1721900000000,
  "webhookEvent": "jira:issue_created",
  "issue": {},
  "user": {},
  "changelog": {}
}
```

---

주요 필드

| Field        | 설명       |
| ------------ | -------- |
| webhookEvent | 이벤트 종류   |
| issue        | Issue 정보 |
| user         | 작업 사용자   |
| changelog    | 변경 내용    |
| timestamp    | 발생 시간    |

---

# 8. Issue Created

Event

```text
jira:issue_created
```

필요 데이터

* Project
* Issue Key
* Summary
* Description
* Reporter
* Assignee
* Priority
* Status
* Issue Type
* URL

Discord

```text
Issue Created

Project
Issue
Summary
Reporter
Assignee
Priority
Status
```

---

# 9. Issue Updated

Event

```text
jira:issue_updated
```

변경된 항목은 changelog에서 확인한다.

예시

```json
{
  "changelog": {
    "items": [
      {
        "field": "status",
        "fromString": "To Do",
        "toString": "Done"
      }
    ]
  }
}
```

Discord

```text
Issue Updated

Issue

Changed Field

Before

After
```

---

# 10. Status Changed

Issue Updated 이벤트 중

```text
field = status
```

Discord

```text
Status Changed

To Do

↓

In Progress
```

---

# 11. Priority Changed

Issue Updated 이벤트 중

```text
field = priority
```

Discord

```text
Priority Changed

Medium

↓

High
```

---

# 12. Assignee Changed

Issue Updated 이벤트 중

```text
field = assignee
```

Discord

```text
Assignee Changed

Old User

↓

New User
```

---

# 13. Comment Created

Event

```text
comment_created
```

필요 데이터

* Comment Author
* Issue
* Repository(Project)
* Comment Body
* URL

Discord

```text
Comment Added

Issue

Author

Preview
```

댓글 본문은 최대 300자로 표시한다.

---

# 14. Comment Updated

Event

```text
comment_updated
```

Discord

```text
Comment Updated

Issue

Editor
```

---

# 15. Comment Deleted

Event

```text
comment_deleted
```

Discord

```text
Comment Deleted

Issue

Deleted By
```

---

# 16. Jira Handler Mapping

| Event              | Handler            |
| ------------------ | ------------------ |
| jira:issue_created | JiraIssueHandler   |
| jira:issue_updated | JiraIssueHandler   |
| jira:issue_deleted | JiraIssueHandler   |
| comment_created    | JiraCommentHandler |
| comment_updated    | JiraCommentHandler |
| comment_deleted    | JiraCommentHandler |

---

# 17. Jira Error Code

| Code  | 의미                  |
| ----- | ------------------- |
| JR001 | Invalid Payload     |
| JR002 | Unsupported Event   |
| JR003 | Missing Issue       |
| JR004 | Missing User        |
| JR005 | Discord Send Failed |

---

# 18. Jira Retry

Discord 실패

↓

Retry

1초

↓

2초

↓

4초

최대 3회

---

# 19. Confluence Event 목록

지원

| Event              | 지원 |
| ------------------ | -- |
| page_created       | O  |
| page_updated       | O  |
| comment_created    | O  |
| attachment_created | O  |

---

# 20. Confluence Payload

대표 구조

```json
{
  "eventType": "page_updated",
  "page": {},
  "user": {},
  "space": {}
}
```

주요 필드

| Field     | 설명       |
| --------- | -------- |
| eventType | 이벤트      |
| page      | 문서 정보    |
| user      | 작업자      |
| space     | Space 정보 |

---

# 21. Page Created

Event

```text
page_created
```

Discord

```text
Document Created

Space

Title

Creator

Created Time
```

필요 데이터

* Space
* Title
* URL
* Creator
* Created Time

---

# 22. Page Updated

Event

```text
page_updated
```

Discord

```text
Document Updated

Title

Editor

Updated Time
```

필요 데이터

* Title
* Modifier
* URL
* Updated Time
* Version

---

# 23. Comment Created

Event

```text
comment_created
```

Discord

```text
Comment Added

Document

Author

Preview
```

댓글은 최대 300자까지 출력한다.

---

# 24. Attachment Uploaded

Event

```text
attachment_created
```

Discord

```text
Attachment Uploaded

Document

File Name

Uploader
```

필요 데이터

* File Name
* File Size(가능한 경우)
* Uploader
* Document
* URL

---

# 25. Confluence Handler Mapping

| Event              | Handler                     |
| ------------------ | --------------------------- |
| page_created       | ConfluencePageHandler       |
| page_updated       | ConfluencePageHandler       |
| comment_created    | ConfluenceCommentHandler    |
| attachment_created | ConfluenceAttachmentHandler |

---

# 26. Discord Embed Mapping

## Jira

색상

Blue

Title

```text
Issue Created
```

Footer

```text
CollabNotify • Jira
```

Button

```text
Open Issue
```

---

## Confluence

색상

Teal

Title

```text
Page Updated
```

Footer

```text
CollabNotify • Confluence
```

Button

```text
Open Document
```

---

# 27. Error Code

## Jira

| Code  | 의미                |
| ----- | ----------------- |
| JR001 | Invalid Payload   |
| JR002 | Missing Issue     |
| JR003 | Missing User      |
| JR004 | Unsupported Event |
| JR005 | Discord Failure   |

---

## Confluence

| Code  | 의미                |
| ----- | ----------------- |
| CF001 | Invalid Payload   |
| CF002 | Missing Page      |
| CF003 | Missing User      |
| CF004 | Unsupported Event |
| CF005 | Discord Failure   |

---

# 28. Retry Policy

Discord API 실패

* 최대 3회 재시도
* 지수 백오프 적용
* 실패 시 ERROR 로그 저장
* Webhook 요청은 즉시 200 OK 반환하고 내부적으로 비동기 처리

---

# 29. Event → Handler → Discord

```text
Jira

↓

Webhook

↓

Router

↓

Dispatcher

↓

Jira Handler

↓

Embed Builder

↓

Discord
```

```text
Confluence

↓

Webhook

↓

Router

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

# 30. OpenAPI 예시

## Jira

```http
POST /api/v1/webhook/jira
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

Response

```json
{
  "success": true,
  "message": "Confluence webhook processed successfully."
}
```
