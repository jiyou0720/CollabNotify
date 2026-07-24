# 04_API_Specification_Part1

# Common API Specification & GitHub Webhook

Project : CollabNotify
Version : 1.0
Status : Draft

---

# 1. 목적

본 문서는 CollabNotify에서 사용하는 모든 Webhook API의 공통 규칙과 GitHub Webhook API 명세를 정의한다.

모든 API는 REST 기반으로 구현하며 JSON Payload를 사용한다.

---

# 2. Base URL

개발

```text
http://localhost:8000
```

운영

```text
https://your-domain.com
```

---

# 3. API Version

```text
v1
```

모든 API는 `/api/v1` 경로를 사용한다.

예시

```text
POST /api/v1/webhook/github
```

---

# 4. Content Type

모든 요청은 다음 Content-Type을 사용한다.

```http
Content-Type: application/json
```

---

# 5. 공통 응답

## 성공

HTTP

```http
200 OK
```

Body

```json
{
  "success": true,
  "message": "Webhook processed successfully."
}
```

---

## 잘못된 요청

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

## 인증 실패

```http
401 Unauthorized
```

```json
{
  "success": false,
  "error": "Invalid signature."
}
```

---

## 지원하지 않는 이벤트

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

## 서버 오류

```http
500 Internal Server Error
```

```json
{
  "success": false,
  "error": "Internal server error."
}
```

---

# 6. 공통 Header

| Header       | Required | 설명               |
| ------------ | -------- | ---------------- |
| Content-Type | Yes      | application/json |
| User-Agent   | Yes      | Webhook Sender   |
| X-Request-ID | No       | 추적용 ID           |

---

# 7. 인증

GitHub는 Webhook Secret 기반 HMAC SHA-256 검증을 사용한다.

Header

```http
X-Hub-Signature-256
```

예시

```text
sha256=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

검증 절차

1. Request Body 읽기
2. Secret 조회
3. HMAC SHA-256 생성
4. Header와 비교
5. 일치하지 않으면 401 반환

---

# 8. Endpoint

## GitHub

```http
POST /api/v1/webhook/github
```

설명

GitHub Webhook 수신 Endpoint

---

# 9. GitHub Header

| Header              | 설명              |
| ------------------- | --------------- |
| X-GitHub-Event      | 이벤트 종류          |
| X-GitHub-Delivery   | UUID            |
| X-Hub-Signature-256 | Signature       |
| User-Agent          | GitHub-Hookshot |

---

# 10. 이벤트 목록

| Event               | 지원 |
| ------------------- | -- |
| issues              | O  |
| issue_comment       | O  |
| pull_request        | O  |
| pull_request_review | O  |
| push                | O  |
| release             | O  |
| workflow_run        | O  |
| create              | O  |
| delete              | O  |

---

# 11. Dispatcher 동작

Router

↓

Signature 검증

↓

X-GitHub-Event 확인

↓

Dispatcher 호출

↓

Handler 선택

↓

Discord Embed 생성

↓

Discord 전송

---

# 12. Issues Event

Header

```http
X-GitHub-Event: issues
```

지원 Action

| Action     |
| ---------- |
| opened     |
| edited     |
| closed     |
| reopened   |
| assigned   |
| unassigned |
| labeled    |
| unlabeled  |

---

Payload 주요 필드

```json
{
  "action": "opened",
  "issue": {
    "number": 15,
    "title": "Login Bug",
    "state": "open",
    "html_url": "...",
    "labels": [],
    "user": {}
  },
  "repository": {},
  "sender": {}
}
```

필요 데이터

* Action
* Repository
* Number
* Title
* State
* Labels
* URL
* Author

---

Discord Embed

Title

```text
Issue Opened
```

Fields

Repository

Issue #

Title

Author

State

Labels

---

# 13. Issue Comment

Header

```http
X-GitHub-Event: issue_comment
```

지원

* created
* edited
* deleted

Payload

```json
{
  "action":"created",
  "comment":{},
  "issue":{},
  "repository":{}
}
```

표시

Repository

Issue

Comment Author

Comment URL

---

# 14. Pull Request

Header

```http
X-GitHub-Event: pull_request
```

지원 Action

* opened
* edited
* synchronize
* reopened
* closed
* ready_for_review
* converted_to_draft
* review_requested
* review_request_removed

Payload

```json
{
  "action":"opened",
  "pull_request":{
      "number":1,
      "title":"API Update",
      "state":"open",
      "merged":false,
      "base":{},
      "head":{},
      "html_url":"..."
  },
  "repository":{}
}
```

필요 데이터

* PR 번호
* 제목
* 작성자
* Base Branch
* Head Branch
* Merge 여부
* URL

---

Discord 표시

Repository

PR

Author

Branch

Status

---

# 15. Pull Request Review

Header

```http
X-GitHub-Event: pull_request_review
```

지원

* submitted
* edited
* dismissed

Payload

```json
{
  "action":"submitted",
  "review":{
      "state":"approved"
  }
}
```

표시

Reviewer

Review State

PR

Repository

---

# 16. Push

Header

```http
X-GitHub-Event: push
```

Payload

```json
{
  "ref":"refs/heads/main",
  "commits":[]
}
```

필요 데이터

* Branch
* Repository
* Commit Count
* Commit Message
* Commit URL
* Commit Author

Discord

```text
Push Event

Repository

Branch

Commit Count
```

---

# 17. Release

Header

```http
X-GitHub-Event: release
```

지원

* published
* unpublished
* created
* edited
* deleted
* prereleased
* released

Payload

```json
{
    "release":{
        "tag_name":"v1.0.0"
    }
}
```

표시

Repository

Version

Release Name

Author

---

# 18. Workflow Run

Header

```http
X-GitHub-Event: workflow_run
```

지원

* requested
* completed

Payload

```json
{
    "workflow_run":{
        "name":"CI",
        "conclusion":"success"
    }
}
```

Discord

Workflow

Branch

Result

Commit

Duration

---

# 19. Create

Header

```http
X-GitHub-Event: create
```

지원

* Branch 생성
* Tag 생성

Payload

```json
{
    "ref_type":"branch",
    "ref":"develop"
}
```

---

# 20. Delete

Header

```http
X-GitHub-Event: delete
```

지원

* Branch 삭제
* Tag 삭제

---

# 21. 이벤트 → Handler 매핑

| Event               | Handler                  |
| ------------------- | ------------------------ |
| issues              | GithubIssueHandler       |
| issue_comment       | GithubCommentHandler     |
| pull_request        | GithubPullRequestHandler |
| pull_request_review | GithubReviewHandler      |
| push                | GithubPushHandler        |
| release             | GithubReleaseHandler     |
| workflow_run        | GithubWorkflowHandler    |
| create              | GithubCreateHandler      |
| delete              | GithubDeleteHandler      |

---

# 22. Error Code

| Code  | 의미                  |
| ----- | ------------------- |
| GH001 | Invalid Signature   |
| GH002 | Missing Header      |
| GH003 | Unsupported Event   |
| GH004 | Invalid Payload     |
| GH005 | Discord Send Failed |

---

# 23. Retry Policy

Discord API 전송 실패 시:

* 최대 3회 재시도
* 재시도 간격: 1초 → 2초 → 4초 (Exponential Backoff)
* 3회 실패 시 Error Log 기록

GitHub Webhook 요청에는 재응답을 지연시키지 않으며, 내부 처리 실패는 로그로 관리한다.

---

# 24. OpenAPI 예시

```http
POST /api/v1/webhook/github
```

Request Headers

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
