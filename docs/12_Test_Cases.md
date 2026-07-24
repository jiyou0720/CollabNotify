# 12_Test_Cases

# Test Cases Specification

Project : CollabNotify
Version : 1.0
Status : Draft

---

# 1. 목적

본 문서는 CollabNotify 시스템의 기능 검증을 위한 테스트 케이스를 정의한다.

테스트 목표

* 기능 검증
* 예외 처리 검증
* 데이터 무결성 검증
* Discord 알림 검증
* Webhook 처리 검증

---

# 2. 테스트 범위

| 구분               | 포함 여부 |
| ---------------- | ----- |
| API Test         | ✅     |
| Unit Test        | ✅     |
| Integration Test | ✅     |
| Database Test    | ✅     |
| Discord Test     | ✅     |
| Performance Test | ✅     |
| Security Test    | ✅     |

---

# 3. 테스트 환경

| 항목          | 값                |
| ----------- | ---------------- |
| Python      | 3.12             |
| FastAPI     | 최신 안정 버전         |
| Discord Bot | Test Server      |
| Database    | SQLite           |
| OS          | Windows / Ubuntu |

---

# 4. API 테스트

## TC-API-001

### 목적

GitHub Webhook 수신 확인

### 입력

```http
POST /api/v1/webhook/github
```

### 기대 결과

* HTTP 200
* 로그 저장
* Dispatcher 호출

---

## TC-API-002

### 목적

Jira Webhook 수신

### 기대 결과

* HTTP 200
* Handler 실행

---

## TC-API-003

### 목적

Confluence Webhook 수신

### 기대 결과

* HTTP 200
* Notification 생성

---

## TC-API-004

### 목적

지원하지 않는 Endpoint 접근

### 입력

```http
POST /api/v1/webhook/test
```

### 기대 결과

```text
404 Not Found
```

---

# 5. GitHub Handler 테스트

## TC-GH-001

Issue Opened

### 입력

GitHub Issue 생성

### 기대 결과

* Notification 생성
* Embed 생성
* Discord 전송

---

## TC-GH-002

Pull Request 생성

기대 결과

* PR 정보 표시
* Author 표시
* Repository 표시

---

## TC-GH-003

Push Event

기대 결과

* Commit 개수 표시
* Branch 표시

---

## TC-GH-004

Release Published

기대 결과

* Version 표시
* Release URL 표시

---

## TC-GH-005

Workflow 완료

기대 결과

* Workflow 상태 표시
* Success / Failure 색상 적용

---

# 6. Jira Handler 테스트

## TC-JIRA-001

Issue Created

기대 결과

* Issue Key
* Status
* Priority 표시

---

## TC-JIRA-002

Issue Updated

기대 결과

변경된 내용 표시

---

## TC-JIRA-003

Status Changed

기대 결과

이전 상태

↓

현재 상태

표시

---

## TC-JIRA-004

Comment Created

기대 결과

댓글 미리보기 표시

---

# 7. Confluence Handler 테스트

## TC-CONF-001

Page Created

기대 결과

* Page 제목
* 작성자

---

## TC-CONF-002

Page Updated

기대 결과

Version 증가 확인

---

## TC-CONF-003

Attachment Uploaded

기대 결과

파일명 표시

---

# 8. Embed 테스트

## TC-EMBED-001

제목 생성

기대 결과

서비스 아이콘 포함

---

## TC-EMBED-002

서비스 색상

GitHub

↓

Purple

---

## TC-EMBED-003

Footer

기대 결과

```text
CollabNotify
```

---

## TC-EMBED-004

Timestamp

항상 표시

---

## TC-EMBED-005

Button

버튼 클릭 시

원본 페이지 이동

---

# 9. Mapping 테스트

## TC-MAP-001

User Mapping 존재

기대 결과

Discord Mention

---

## TC-MAP-002

User Mapping 없음

기대 결과

사용자 이름만 표시

---

## TC-MAP-003

Role Mapping 존재

기대 결과

Role Mention

---

# 10. Database 테스트

## TC-DB-001

Notification 저장

기대 결과

Database Insert 성공

---

## TC-DB-002

Error 저장

기대 결과

Error Log 생성

---

## TC-DB-003

중복 Event

기대 결과

중복 저장 방지

---

# 11. Dispatcher 테스트

## TC-DIS-001

GitHub Event

기대 결과

GithubHandler 선택

---

## TC-DIS-002

Jira Event

기대 결과

JiraHandler 선택

---

## TC-DIS-003

지원하지 않는 Event

기대 결과

UnsupportedEventException 발생

---

# 12. Discord 테스트

## TC-DS-001

Embed 전송

기대 결과

메시지 생성

---

## TC-DS-002

잘못된 Channel

기대 결과

ChannelNotFoundException

---

## TC-DS-003

Discord API 실패

기대 결과

Retry 수행

---

# 13. Retry 테스트

## TC-RT-001

첫 번째 실패

기대 결과

Retry 예약

---

## TC-RT-002

세 번째 실패

기대 결과

FAILED 저장

---

# 14. Security 테스트

## TC-SEC-001

GitHub Signature 검증 성공

기대 결과

HTTP 200

---

## TC-SEC-002

Signature 오류

기대 결과

HTTP 401

---

## TC-SEC-003

Payload 변조

기대 결과

요청 거부

---

# 15. 예외 처리 테스트

## TC-EX-001

잘못된 JSON

기대 결과

400 Bad Request

---

## TC-EX-002

필수 필드 누락

기대 결과

Validation Error

---

## TC-EX-003

Discord API Timeout

기대 결과

Retry

---

# 16. 성능 테스트

## TC-PERF-001

Webhook 응답

목표

```text
< 500ms
```

---

## TC-PERF-002

Embed 생성

목표

```text
< 100ms
```

---

## TC-PERF-003

Notification 처리

목표

```text
< 1초
```

---

# 17. 부하 테스트

## TC-LOAD-001

100개의 Webhook

기대 결과

모두 처리

---

## TC-LOAD-002

동시 요청

20개

기대 결과

오류 없음

---

# 18. 통합 테스트

## TC-INT-001

GitHub

↓

Webhook

↓

Dispatcher

↓

Handler

↓

Discord

성공

---

## TC-INT-002

Jira

↓

Webhook

↓

Discord

성공

---

## TC-INT-003

Confluence

↓

Webhook

↓

Discord

성공

---

# 19. 회귀 테스트

다음 기능이 기존 동작에 영향을 주지 않아야 한다.

* GitHub Issue
* GitHub PR
* Jira Issue
* Confluence Page
* Discord Embed

---

# 20. 테스트 데이터

GitHub

* Issue 생성
* Pull Request 생성
* Push
* Release

Jira

* Issue 생성
* Status 변경
* Comment

Confluence

* Page 생성
* Attachment 업로드

---

# 21. 테스트 성공 기준

| 항목               | 기준      |
| ---------------- | ------- |
| Unit Test        | 100% 통과 |
| Integration Test | 100% 통과 |
| API Test         | 100% 통과 |
| Security Test    | 100% 통과 |
| Database Test    | 100% 통과 |

---

# 22. 품질 기준

* 테스트 커버리지 80% 이상
* 치명적(Critical) 버그 0건
* 높은(High) 우선순위 버그 0건
* 모든 P0 기능 정상 동작

---

# 23. 자동화 테스트

권장 도구

* pytest
* pytest-cov
* httpx(TestClient)
* unittest.mock

CI 실행 항목

* Unit Test
* Integration Test
* Lint(Ruff)
* Format(Black)

---

# 24. 테스트 체크리스트

## API

* [ ] GitHub Webhook
* [ ] Jira Webhook
* [ ] Confluence Webhook

## Discord

* [ ] Embed 생성
* [ ] Button 동작
* [ ] Mention 동작

## Database

* [ ] Notification 저장
* [ ] Error 저장
* [ ] Mapping 조회

## Security

* [ ] Signature 검증
* [ ] 잘못된 Payload 차단

## Performance

* [ ] 응답 시간 확인
* [ ] 동시 요청 처리

---

# 25. 완료 기준

다음 조건을 만족하면 테스트가 완료된 것으로 판단한다.

* 모든 테스트 케이스가 성공한다.
* 치명적인 오류(Critical Bug)가 존재하지 않는다.
* 기능 요구사항(PRD)을 모두 만족한다.
* 테스트 커버리지가 80% 이상이다.
* Discord 알림이 정상적으로 전송된다.
* 운영 환경과 동일한 환경에서 통합 테스트를 통과한다.
