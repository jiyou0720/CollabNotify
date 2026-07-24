# 06_Database_Design

# Database Design Specification

Project : CollabNotify
Version : 1.0
Status : Draft

---

# 1. 목적

본 문서는 CollabNotify에서 사용하는 데이터베이스 구조를 정의한다.

데이터베이스는 다음 정보를 저장한다.

* 시스템 설정
* Discord 채널 설정
* 프로젝트 매핑
* 사용자 매핑
* 이벤트 로그
* 오류 로그

초기 버전은 SQLite를 사용하며, 추후 PostgreSQL로 마이그레이션할 수 있도록 설계한다.

---

# 2. DBMS

## MVP

* SQLite 3

## 향후 확장

* PostgreSQL
* MySQL (선택)

ORM은 SQLAlchemy를 사용한다.

---

# 3. ERD

```text
                 +----------------------+
                 |      projects        |
                 +----------------------+
                          |
                          |
             +------------+------------+
             |                         |
             |                         |
             ▼                         ▼
     channel_mappings          user_mappings

             |
             |
             ▼

      notification_logs

             |
             ▼

         error_logs

             |
             ▼

          settings
```

---

# 4. projects

프로젝트 또는 저장소 정보를 저장한다.

| Column      | Type     | Constraint   |
| ----------- | -------- | ------------ |
| id          | INTEGER  | PK           |
| name        | TEXT     | NOT NULL     |
| service     | TEXT     | NOT NULL     |
| external_id | TEXT     | UNIQUE       |
| enabled     | BOOLEAN  | DEFAULT TRUE |
| created_at  | DATETIME | NOT NULL     |
| updated_at  | DATETIME | NOT NULL     |

예시

| name       | service    |
| ---------- | ---------- |
| CampusFlow | github     |
| CampusFlow | jira       |
| Wiki       | confluence |

---

# 5. channel_mappings

서비스별 Discord 채널을 관리한다.

| Column             | Type     |
| ------------------ | -------- |
| id                 | INTEGER  |
| service            | TEXT     |
| project_id         | INTEGER  |
| discord_channel_id | TEXT     |
| created_at         | DATETIME |

Foreign Key

```text
project_id → projects.id
```

예시

| Service    | Discord Channel |
| ---------- | --------------- |
| github     | 1357924680      |
| jira       | 1357924681      |
| confluence | 1357924682      |

---

# 6. user_mappings

외부 서비스 사용자와 Discord 사용자를 연결한다.

| Column               | Type     |
| -------------------- | -------- |
| id                   | INTEGER  |
| service              | TEXT     |
| external_username    | TEXT     |
| discord_user_id      | TEXT     |
| discord_display_name | TEXT     |
| created_at           | DATETIME |

예시

| Service | External  | Discord   |
| ------- | --------- | --------- |
| github  | jiyupark  | 123456789 |
| jira    | jiyu.park | 123456789 |

활용

* Reviewer 멘션
* Assignee 멘션
* Comment 작성자 표시

---

# 7. role_mappings

Discord 역할(Role)과 프로젝트를 연결한다.

| Column          | Type    |
| --------------- | ------- |
| id              | INTEGER |
| project_id      | INTEGER |
| role_name       | TEXT    |
| discord_role_id | TEXT    |

예시

| Project    | Role     |
| ---------- | -------- |
| CampusFlow | Backend  |
| CampusFlow | Frontend |

---

# 8. notification_logs

Discord로 전송한 모든 이벤트를 저장한다.

| Column             | Type     |
| ------------------ | -------- |
| id                 | INTEGER  |
| service            | TEXT     |
| event_type         | TEXT     |
| project_id         | INTEGER  |
| external_event_id  | TEXT     |
| discord_message_id | TEXT     |
| status             | TEXT     |
| processed_at       | DATETIME |

Status

* SUCCESS
* FAILED
* RETRY

목적

* 중복 전송 방지
* 감사(Audit)
* 통계

---

# 9. error_logs

시스템 오류를 저장한다.

| Column      | Type     |
| ----------- | -------- |
| id          | INTEGER  |
| error_code  | TEXT     |
| service     | TEXT     |
| message     | TEXT     |
| payload     | TEXT     |
| stack_trace | TEXT     |
| created_at  | DATETIME |

payload는 JSON 문자열로 저장한다.

---

# 10. settings

시스템 전역 설정을 저장한다.

| Column     | Type     |
| ---------- | -------- |
| id         | INTEGER  |
| key        | TEXT     |
| value      | TEXT     |
| updated_at | DATETIME |

예시

| Key            | Value |
| -------------- | ----- |
| retry_count    | 3     |
| retry_interval | 1     |
| log_level      | INFO  |

---

# 11. recommended_indexes

## projects

```sql
CREATE INDEX idx_projects_service
ON projects(service);
```

---

## user_mappings

```sql
CREATE INDEX idx_user_service
ON user_mappings(service, external_username);
```

---

## notification_logs

```sql
CREATE INDEX idx_notification_event
ON notification_logs(event_type);
```

```sql
CREATE INDEX idx_notification_processed
ON notification_logs(processed_at);
```

---

## error_logs

```sql
CREATE INDEX idx_error_created
ON error_logs(created_at);
```

---

# 12. Entity 관계

```text
Projects

1

↓

N

ChannelMappings

Projects

1

↓

N

RoleMappings

Projects

1

↓

N

NotificationLogs
```

UserMapping은 독립 엔티티로 관리한다.

---

# 13. Notification Lifecycle

```text
Webhook

↓

Dispatcher

↓

Handler

↓

NotificationLogs 생성

↓

Discord 전송

↓

성공

↓

Status = SUCCESS
```

실패

```text
FAILED

↓

Retry

↓

SUCCESS

또는

FAILED
```

---

# 14. 삭제 정책

## Projects

삭제 시

↓

Channel Mapping 삭제

↓

Role Mapping 삭제

Notification Log는 삭제하지 않는다.

---

## Notification Logs

기본 보관

90일

이후 자동 삭제 가능

---

## Error Logs

기본 보관

180일

---

# 15. 데이터 무결성

* Primary Key는 Auto Increment 사용
* Foreign Key 제약조건 활성화
* UNIQUE 제약조건으로 중복 매핑 방지
* NOT NULL 제약조건 적용

---

# 16. 트랜잭션 정책

다음 작업은 하나의 트랜잭션으로 처리한다.

* NotificationLog 생성
* Discord 전송 결과 저장

성공 시 Commit

실패 시 Rollback

---

# 17. 성능 고려사항

* 자주 조회하는 컬럼은 Index 생성
* Payload 전체는 로그에만 저장
* 외부 서비스 ID를 기준으로 검색
* Notification Log는 페이지네이션 지원

---

# 18. 백업 정책

SQLite Database

* 하루 1회 백업
* 최근 7일 보관

PostgreSQL 전환 시

* WAL 기반 백업 적용
* Point-in-Time Recovery(PITR) 고려

---

# 19. 향후 확장

추가 예정 테이블

| Table              | 목적                  |
| ------------------ | ------------------- |
| webhook_history    | 원본 Webhook 저장       |
| retry_queue        | 재시도 큐               |
| api_keys           | 관리자 API Key         |
| audit_logs         | 관리자 작업 로그           |
| dashboards         | 대시보드 설정             |
| notification_rules | 알림 필터 규칙            |
| discord_servers    | 다중 서버 지원            |
| repositories       | GitHub 저장소 정보       |
| jira_projects      | Jira 프로젝트 정보        |
| confluence_spaces  | Confluence Space 정보 |

---

# 20. 완료 기준

다음 조건을 만족하면 데이터베이스 설계가 완료된 것으로 판단한다.

* 모든 핵심 엔티티가 정의되어 있다.
* 프로젝트와 Discord 채널을 매핑할 수 있다.
* 사용자 및 역할 매핑을 지원한다.
* 이벤트 및 오류 로그를 저장할 수 있다.
* 확장 가능한 관계 구조를 가진다.
* SQLite와 PostgreSQL 모두에서 사용 가능한 스키마를 제공한다.
