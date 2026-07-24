# 10_TODO

# Development TODO & Roadmap

Project : CollabNotify
Version : 1.0
Status : Draft

---

# 1. 목적

본 문서는 CollabNotify 프로젝트의 개발 작업 목록(TODO), 우선순위, 예상 소요 시간 및 완료 기준을 정의한다.

작업은 다음 기준으로 관리한다.

* 우선순위(Priority)
* 개발 단계(Milestone)
* 완료 여부(Status)
* 예상 소요 시간(Estimate)
* 완료 기준(Definition of Done)

---

# 2. 우선순위 기준

| Priority | 설명                    |
| -------- | --------------------- |
| P0       | 서비스 실행에 반드시 필요한 핵심 기능 |
| P1       | MVP 완성에 필요한 기능        |
| P2       | 편의 기능 및 운영 기능         |
| P3       | 향후 확장 기능              |

---

# 3. 개발 단계

| Milestone | 내용              |
| --------- | --------------- |
| M1        | 프로젝트 초기 환경 구축   |
| M2        | Webhook 수신 및 처리 |
| M3        | Discord 알림 전송   |
| M4        | 데이터베이스 및 로그     |
| M5        | 테스트 및 배포        |
| M6        | 운영 기능 및 확장      |

---

# 4. M1 - 프로젝트 초기 환경 구축

| 상태 | Priority | 작업             | 예상 시간 |
| -- | -------- | -------------- | ----- |
| ☐  | P0       | 프로젝트 생성        | 30분   |
| ☐  | P0       | Git 저장소 생성     | 10분   |
| ☐  | P0       | Python 가상환경 구성 | 20분   |
| ☐  | P0       | FastAPI 설치     | 15분   |
| ☐  | P0       | Discord Bot 생성 | 30분   |
| ☐  | P0       | SQLAlchemy 설정  | 30분   |
| ☐  | P0       | SQLite 연결      | 20분   |
| ☐  | P0       | 환경 변수(.env) 구성 | 20분   |
| ☐  | P1       | Docker 환경 구성   | 1시간   |
| ☐  | P1       | Logging 설정     | 30분   |

**완료 기준**

* FastAPI 실행 확인
* Discord Bot 로그인 성공
* SQLite 연결 성공

---

# 5. M2 - Webhook 수신

## GitHub

| 상태 | Priority | 작업                  | 예상 시간 |
| -- | -------- | ------------------- | ----- |
| ☐  | P0       | Webhook Endpoint 생성 | 40분   |
| ☐  | P0       | Signature 검증        | 1시간   |
| ☐  | P0       | Issue 이벤트 처리        | 2시간   |
| ☐  | P0       | Pull Request 이벤트 처리 | 2시간   |
| ☐  | P1       | Push 이벤트 처리         | 1시간   |
| ☐  | P1       | Review 이벤트 처리       | 1시간   |
| ☐  | P2       | Release 이벤트 처리      | 40분   |
| ☐  | P2       | Workflow 이벤트 처리     | 40분   |

---

## Jira

| 상태 | Priority | 작업              | 예상 시간 |
| -- | -------- | --------------- | ----- |
| ☐  | P0       | Endpoint 생성     | 30분   |
| ☐  | P0       | Issue 생성 이벤트    | 1시간   |
| ☐  | P0       | Issue 수정 이벤트    | 1시간   |
| ☐  | P1       | Status 변경 이벤트   | 1시간   |
| ☐  | P1       | Priority 변경 이벤트 | 40분   |
| ☐  | P2       | Comment 이벤트     | 1시간   |

---

## Confluence

| 상태 | Priority | 작업             | 예상 시간 |
| -- | -------- | -------------- | ----- |
| ☐  | P1       | Endpoint 생성    | 30분   |
| ☐  | P1       | Page 생성 이벤트    | 1시간   |
| ☐  | P1       | Page 수정 이벤트    | 1시간   |
| ☐  | P2       | Attachment 이벤트 | 40분   |
| ☐  | P2       | Comment 이벤트    | 40분   |

**완료 기준**

* GitHub Webhook 정상 수신
* Jira Webhook 정상 수신
* Confluence Webhook 정상 수신

---

# 6. M3 - Discord 알림

| 상태 | Priority | 작업                 | 예상 시간 |
| -- | -------- | ------------------ | ----- |
| ☐  | P0       | DiscordService 구현  | 2시간   |
| ☐  | P0       | EmbedBuilder 구현    | 2시간   |
| ☐  | P0       | GitHub Embed       | 2시간   |
| ☐  | P0       | Jira Embed         | 2시간   |
| ☐  | P1       | Confluence Embed   | 1시간   |
| ☐  | P1       | 버튼(View/Button) 구현 | 1시간   |
| ☐  | P1       | 사용자 멘션             | 1시간   |
| ☐  | P2       | 역할(Role) 멘션        | 1시간   |

**완료 기준**

* Discord Embed 전송 성공
* 버튼 정상 동작
* 서비스별 색상 적용

---

# 7. M4 - 데이터베이스 및 로그

| 상태 | Priority | 작업               | 예상 시간 |
| -- | -------- | ---------------- | ----- |
| ☐  | P0       | Project 테이블      | 30분   |
| ☐  | P0       | Channel Mapping  | 30분   |
| ☐  | P0       | User Mapping     | 1시간   |
| ☐  | P0       | Notification Log | 1시간   |
| ☐  | P1       | Error Log        | 40분   |
| ☐  | P1       | Repository 구현    | 2시간   |
| ☐  | P2       | Migration 적용     | 1시간   |

**완료 기준**

* 모든 로그 저장
* CRUD 정상 동작
* Repository 테스트 통과

---

# 8. M5 - 테스트 및 품질 관리

| 상태 | Priority | 작업                 | 예상 시간 |
| -- | -------- | ------------------ | ----- |
| ☐  | P0       | Dispatcher 테스트     | 1시간   |
| ☐  | P0       | Handler 테스트        | 2시간   |
| ☐  | P0       | DiscordService 테스트 | 1시간   |
| ☐  | P0       | Repository 테스트     | 1시간   |
| ☐  | P1       | Integration Test   | 2시간   |
| ☐  | P1       | API Test           | 1시간   |
| ☐  | P2       | Coverage 확인        | 30분   |

**완료 기준**

* Unit Test 통과
* Integration Test 통과
* 테스트 커버리지 80% 이상

---

# 9. M6 - 운영 기능

| 상태 | Priority | 작업             | 예상 시간 |
| -- | -------- | -------------- | ----- |
| ☐  | P1       | Retry Worker   | 2시간   |
| ☐  | P1       | Cleanup Worker | 1시간   |
| ☐  | P2       | 통계 기능          | 2시간   |
| ☐  | P2       | 관리자 설정         | 2시간   |
| ☐  | P2       | 로그 백업          | 1시간   |

---

# 10. 향후 기능 (P3)

| 상태 | 작업                 |
| -- | ------------------ |
| ☐  | GitLab 지원          |
| ☐  | Slack 지원           |
| ☐  | Microsoft Teams 지원 |
| ☐  | Jenkins 연동         |
| ☐  | CI/CD 알림           |
| ☐  | AI 요약 기능           |
| ☐  | 알림 규칙(Filter)      |
| ☐  | Web Dashboard      |
| ☐  | 다중 Discord 서버 지원   |
| ☐  | 다국어 지원             |

---

# 11. Definition of Done (DoD)

작업이 완료되었다고 판단하기 위한 기준

* 기능이 정상 동작한다.
* 예외 처리가 구현되어 있다.
* 로그가 기록된다.
* 테스트 코드가 작성되어 있다.
* 코드 리뷰를 통과하였다.
* 문서가 최신 상태로 업데이트되었다.

---

# 12. 릴리스 체크리스트

## Alpha

* [ ] FastAPI 실행
* [ ] Discord Bot 연결
* [ ] GitHub Webhook 처리

---

## Beta

* [ ] Jira 지원
* [ ] Confluence 지원
* [ ] 데이터베이스 저장
* [ ] 테스트 완료

---

## v1.0

* [ ] 모든 핵심 기능 구현
* [ ] 문서 작성 완료
* [ ] Docker 배포 확인
* [ ] 운영 테스트 완료

---

# 13. 위험 요소(Risk)

| 위험 요소              | 대응 방안                |
| ------------------ | -------------------- |
| Discord API 제한     | 재시도 및 Rate Limit 처리  |
| Webhook Payload 변경 | 스키마 검증 및 버전 관리       |
| 네트워크 장애            | Retry Worker 적용      |
| 중복 이벤트 수신          | Event ID 기반 중복 제거    |
| 인증 실패              | Signature 검증 및 로그 기록 |

---

# 14. 예상 개발 일정

| 단계 | 예상 기간 |
| -- | ----- |
| M1 | 1일    |
| M2 | 3일    |
| M3 | 2일    |
| M4 | 2일    |
| M5 | 2일    |
| M6 | 2일    |

**총 예상 개발 기간**

약 **12일**

---

# 15. 최종 완료 조건

다음 조건을 만족하면 CollabNotify MVP 개발이 완료된 것으로 판단한다.

* GitHub, Jira, Confluence Webhook을 정상적으로 수신한다.
* Discord Embed 알림이 정상적으로 전송된다.
* 사용자 및 채널 매핑이 정상 동작한다.
* 이벤트 및 오류 로그가 데이터베이스에 저장된다.
* 단위 테스트와 통합 테스트를 통과한다.
* Docker 환경에서 정상 실행된다.
* 프로젝트 문서(PRD, API, 아키텍처, 클래스 설계 등)가 최신 상태로 유지된다.
