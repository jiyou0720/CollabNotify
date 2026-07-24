# 05_Discord_UI_Guide

# Discord UI Design Guide

Project : CollabNotify
Version : 1.0
Status : Draft

---

# 1. 목적

본 문서는 CollabNotify에서 생성되는 모든 Discord 알림의 UI 규칙을 정의한다.

모든 알림은 일관된 디자인을 유지해야 하며, 사용자가 이벤트를 빠르게 이해할 수 있도록 정보의 배치와 표현 방식을 표준화한다.

---

# 2. 디자인 원칙

## 일관성 (Consistency)

* 모든 이벤트는 동일한 레이아웃을 사용한다.
* 동일한 의미의 정보는 항상 같은 위치에 표시한다.

---

## 가독성 (Readability)

* 핵심 정보는 상단에 배치한다.
* Field 이름은 짧고 명확하게 작성한다.
* 불필요한 장식은 사용하지 않는다.

---

## 즉시성 (Visibility)

사용자는 Embed를 보는 즉시 다음 정보를 알 수 있어야 한다.

* 어떤 서비스에서 발생한 이벤트인지
* 어떤 종류의 이벤트인지
* 누가 수행했는지
* 무엇이 변경되었는지
* 어디에서 발생했는지

---

# 3. 서비스 색상

| 서비스        | 색상     | HEX     |
| ---------- | ------ | ------- |
| GitHub     | Purple | #6F42C1 |
| Jira       | Blue   | #0052CC |
| Confluence | Teal   | #008DA6 |
| Success    | Green  | #2ECC71 |
| Warning    | Orange | #F39C12 |
| Error      | Red    | #E74C3C |

---

# 4. 아이콘

| 서비스        | Emoji |
| ---------- | ----- |
| GitHub     | 🟣    |
| Jira       | 🔵    |
| Confluence | 🟢    |
| Success    | ✅     |
| Warning    | ⚠️    |
| Error      | ❌     |

---

# 5. Embed 기본 구조

모든 Embed는 아래 순서를 따른다.

```text
Title

Description

Field 1

Field 2

Field 3

...

Buttons

Footer

Timestamp
```

---

# 6. Embed Header

형식

```text
[아이콘] [이벤트명]
```

예시

```text
🟣 Pull Request Opened
```

```text
🔵 Issue Created
```

```text
🟢 Page Updated
```

---

# 7. Description 규칙

Description은 이벤트를 한 문장으로 요약한다.

예시

```text
박지유님이 새로운 Pull Request를 생성했습니다.
```

```text
Issue 상태가 변경되었습니다.
```

```text
문서가 수정되었습니다.
```

---

# 8. 공통 Field 순서

모든 Embed는 가능한 한 다음 순서를 따른다.

| 순서 | 항목                   |
| -- | -------------------- |
| 1  | Project / Repository |
| 2  | Issue / PR / Page    |
| 3  | Author               |
| 4  | Assignee             |
| 5  | Status               |
| 6  | Priority             |
| 7  | Branch               |
| 8  | Labels               |
| 9  | Version              |
| 10 | Time                 |

해당하지 않는 항목은 생략한다.

---

# 9. GitHub UI

## Pull Request

```text
🟣 Pull Request Opened

새로운 Pull Request가 생성되었습니다.

Repository
CampusFlow

PR
#52

Title
로그인 API 개선

Author
박지유

Base
main

Head
feature/login

Status
Open
```

Button

```text
Open Pull Request
```

---

## Push

```text
🟣 Push

Repository
CampusFlow

Branch
main

Commit Count
3

Author
박지유
```

Button

```text
Open Commit
```

---

## Release

```text
🟣 Release Published

Repository
CampusFlow

Version
v1.0.0

Author
박지유
```

---

# 10. Jira UI

## Issue Created

```text
🔵 Issue Created

Project
CampusFlow

Issue
CF-102

Title
로그인 오류 수정

Reporter
박지유

Assignee
김철수

Priority
High

Status
To Do
```

Button

```text
Open Issue
```

---

## Status Changed

```text
🔵 Status Changed

Issue
CF-102

Previous
To Do

Current
In Progress
```

---

## Comment Added

```text
🔵 Comment Added

Issue
CF-102

Author
박지유

Preview
로그인 오류를 수정했습니다...
```

댓글 미리보기는 최대 300자로 제한한다.

---

# 11. Confluence UI

## Page Created

```text
🟢 Page Created

Space
Development

Title
API 명세서

Author
박지유

Created
2026-07-24
```

Button

```text
Open Document
```

---

## Page Updated

```text
🟢 Page Updated

Title
시스템 아키텍처

Editor
박지유

Version
5
```

---

## Attachment Uploaded

```text
🟢 Attachment Uploaded

Document
API 명세서

File
architecture.png

Uploader
박지유
```

---

# 12. Footer

기본 Footer

```text
CollabNotify
```

서비스별 Footer

```text
CollabNotify • GitHub
```

```text
CollabNotify • Jira
```

```text
CollabNotify • Confluence
```

---

# 13. Timestamp

모든 Embed에는 Timestamp를 포함한다.

예시

```text
2026-07-24 21:15
```

Discord Native Timestamp 사용을 권장한다.

---

# 14. Thumbnail

서비스별 공식 아이콘을 사용한다.

| 서비스        | 아이콘             |
| ---------- | --------------- |
| GitHub     | GitHub Logo     |
| Jira       | Jira Logo       |
| Confluence | Confluence Logo |

---

# 15. Button 규칙

최대 3개의 버튼을 제공한다.

우선순위

1. 원본 페이지 이동
2. 관련 문서 이동
3. 저장소 이동

예시

```text
[Open Issue]

[Open Project]

[Open Repository]
```

---

# 16. Mention 규칙

사용자 매핑이 존재할 경우 Discord 멘션을 표시한다.

예시

```text
Reviewer

@박지유
```

역할(Role) 매핑이 존재하면 역할을 멘션한다.

```text
@Backend Team
```

---

# 17. 긴 텍스트 처리

Description

* 최대 500자

Comment Preview

* 최대 300자

Commit Message

* 최대 150자

초과하는 경우

```text
...
```

을 붙여 생략한다.

---

# 18. 색상 규칙

성공

```text
Green
```

실패

```text
Red
```

경고

```text
Orange
```

정보

```text
Blue
```

---

# 19. 반응(Reaction)

향후 지원

* 👍 승인
* 👀 확인
* ✅ 완료
* ❌ 거절

---

# 20. UI 예시

## GitHub

```text
🟣 Pull Request Opened

새로운 Pull Request가 생성되었습니다.

Repository
CampusFlow

PR
#41

Title
JWT 인증 추가

Author
박지유

Base
main

Head
feature/jwt

Status
Open

────────────────────────────

[Open Pull Request]

CollabNotify • GitHub
```

---

## Jira

```text
🔵 Issue Updated

Project
CampusFlow

Issue
CF-201

Title
로그인 실패 수정

Priority
High

Status
Done

────────────────────────────

[Open Issue]

CollabNotify • Jira
```

---

## Confluence

```text
🟢 Page Updated

Space
Development

Title
API Specification

Editor
박지유

Version
12

────────────────────────────

[Open Document]

CollabNotify • Confluence
```

---

# 21. 접근성

* 이모지 없이도 제목만으로 이벤트를 구분할 수 있어야 한다.
* 색상만으로 의미를 전달하지 않는다.
* 모든 중요한 정보는 Field 또는 Description에 텍스트로 표시한다.
* 버튼은 명확한 동사(Open, View 등)를 사용한다.

---

# 22. 완료 기준

다음 조건을 만족하면 UI 구현이 완료된 것으로 판단한다.

* 모든 이벤트가 동일한 레이아웃을 사용한다.
* 서비스별 색상이 일관되게 적용된다.
* 버튼이 정상적으로 동작한다.
* Footer와 Timestamp가 항상 표시된다.
* 긴 텍스트가 지정된 길이 내에서 자연스럽게 표시된다.
* 사용자와 역할 멘션이 올바르게 동작한다.
* 모든 Embed가 Discord에서 가독성 있게 표시된다.
