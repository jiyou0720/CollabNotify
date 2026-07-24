# 02. Product Requirements Document (PRD)

# CollabNotify

> Jira · Confluence · GitHub 통합 Discord 알림 시스템

Version: 1.0
Status: Draft

---

# 1. 문서 목적

본 문서는 CollabNotify의 기능 요구사항(Function Requirements)과 비기능 요구사항(Non-functional Requirements)을 정의한다.

이 문서를 기준으로 시스템 설계 및 개발을 진행한다.

---

# 2. 프로젝트 목표

CollabNotify는 Jira, Confluence, GitHub에서 발생하는 이벤트를 Discord로 실시간 전달하여 프로젝트 협업 효율을 높이는 것을 목표로 한다.

사용자는 Discord 하나만으로 프로젝트 진행 상황을 확인할 수 있어야 한다.

---

# 3. 사용자

## 관리자(Admin)

권한

* Discord Bot 설정
* Webhook 등록
* 채널 설정
* 프로젝트 설정
* 사용자 매핑 관리

---

## 개발자(Developer)

권한

* GitHub 이벤트 확인
* Jira 이벤트 확인
* PR 확인
* Review 확인

---

## 기획자(Project Manager)

권한

* Jira 진행 상황 확인
* Confluence 문서 변경 확인
* 일정 관리

---

## 일반 팀원(Member)

권한

* 모든 알림 조회
* 링크 이동

---

# 4. 지원 플랫폼

* Jira Cloud
* Confluence Cloud
* GitHub
* Discord

---

# 5. 주요 기능

## Epic 1. Jira 연동

### User Story

프로젝트 팀원으로서

Jira에서 발생한 이벤트를 Discord에서 즉시 확인하고 싶다.

---

### 지원 이벤트

* Issue Created
* Issue Updated
* Issue Deleted
* Issue Assigned
* Issue Commented
* Status Changed
* Priority Changed

---

### Discord 표시 정보

* 이벤트 종류
* 프로젝트명
* Issue Key
* 제목
* 작성자
* 담당자
* 상태
* 우선순위
* 발생 시각
* 바로가기 링크

---

### 완료 기준

Webhook 수신 후 3초 이내 Discord 전송

---

# Epic 2. Confluence 연동

### User Story

프로젝트 팀원으로서

문서가 수정되면 Discord에서 즉시 확인하고 싶다.

---

### 지원 이벤트

* Page Created
* Page Updated
* Comment Created
* Attachment Uploaded

---

### Discord 표시 정보

* 이벤트 종류
* Space 이름
* 문서 제목
* 생성자
* 수정자
* 생성 시각
* 수정 시각
* 링크

---

### 완료 기준

모든 문서 변경 사항이 Discord에 표시되어야 한다.

---

# Epic 3. GitHub 연동

### User Story

개발자로서

Repository에서 발생하는 이벤트를 Discord에서 확인하고 싶다.

---

## Issue

지원

* Opened
* Closed
* Reopened
* Edited

표시

* 번호
* 제목
* 작성자
* Labels
* Repository

---

## Pull Request

지원

* Opened
* Closed
* Reopened
* Review Requested
* Review Submitted
* Merged
* Converted to Draft
* Ready for Review

표시

* 번호
* 제목
* 작성자
* Base Branch
* Head Branch
* Merge 여부

---

## Push

표시

* Repository
* Branch
* Commit 수
* Commit 목록
* Push 사용자

---

## Release

표시

* Version
* Tag
* 작성자

---

## GitHub Actions

지원

* Success
* Failure
* Cancelled

표시

* Workflow
* Branch
* Commit
* 결과

---

### 완료 기준

GitHub 이벤트가 Discord에 정상 표시되어야 한다.

---

# Epic 4. Discord

## Embed

모든 이벤트는 Embed 형태로 표시한다.

---

## 버튼

각 Embed에는 원본 서비스 이동 버튼이 존재해야 한다.

예

* Open Issue
* Open Document
* Open Pull Request

---

## 색상

Jira

Blue

Confluence

Teal

GitHub

Purple

Success

Green

Failure

Red

Warning

Orange

---

## Footer

항상 표시

CollabNotify

---

## Timestamp

Discord Timestamp 사용

---

# 6. 기능 요구사항

## FR-001

Webhook를 수신할 수 있어야 한다.

Priority

Critical

---

## FR-002

Webhook Secret을 검증해야 한다.

Priority

Critical

---

## FR-003

이벤트 종류를 자동으로 판별해야 한다.

Priority

Critical

---

## FR-004

Discord Embed를 생성해야 한다.

Priority

Critical

---

## FR-005

Discord Bot이 Embed를 전송해야 한다.

Priority

Critical

---

## FR-006

버튼을 생성해야 한다.

Priority

High

---

## FR-007

프로젝트별 Discord 채널을 설정할 수 있어야 한다.

Priority

Medium

---

## FR-008

Repository별 Discord 채널을 설정할 수 있어야 한다.

Priority

Medium

---

## FR-009

Discord 역할(Role) 멘션을 지원해야 한다.

Priority

Medium

---

## FR-010

이벤트 로그를 저장해야 한다.

Priority

Medium

---

# 7. 비기능 요구사항

## 성능

Webhook 수신 후

3초 이내 Discord 전송

---

## 안정성

Webhook 처리 실패 시

재시도 가능해야 한다.

---

## 보안

Webhook Secret 검증

환경 변수 관리

민감 정보 로그 출력 금지

---

## 유지보수

Handler 기반 구조

서비스 계층 분리

비즈니스 로직 분리

---

## 확장성

새로운 협업 도구 추가 시

Handler만 추가하면 동작해야 한다.

---

# 8. 사용자 시나리오

## Jira

개발자가 Issue 생성

↓

Jira Webhook

↓

FastAPI

↓

Dispatcher

↓

Jira Handler

↓

Discord Embed 생성

↓

Discord 전송

---

## GitHub

개발자가 PR Merge

↓

Webhook

↓

Dispatcher

↓

Github Handler

↓

Discord

---

## Confluence

문서 수정

↓

Webhook

↓

Dispatcher

↓

Confluence Handler

↓

Discord

---

# 9. 예외 처리

Webhook Secret 불일치

↓

401 반환

---

지원하지 않는 이벤트

↓

무시

---

Discord API 실패

↓

재시도

↓

실패 로그 기록

---

# 10. MVP 범위

포함

* Jira
* GitHub
* Confluence
* Discord
* Embed
* Button
* Secret 검증

제외

* 웹 관리자
* OAuth
* DB 관리 페이지
* Slack
* GitLab

---

# 11. 성공 기준

다음 조건을 모두 만족하면 MVP를 완료한 것으로 판단한다.

* Jira 이벤트를 실시간으로 수신하고 Discord에 표시할 수 있다.
* Confluence 이벤트를 실시간으로 수신하고 Discord에 표시할 수 있다.
* GitHub 이벤트를 실시간으로 수신하고 Discord에 표시할 수 있다.
* 모든 알림은 Discord Embed 형식으로 출력된다.
* Embed에는 원본 서비스로 이동하는 버튼이 포함된다.
* 이벤트별 채널 분리가 가능하다.
* Webhook Secret 검증이 정상 동작한다.
* 예외 발생 시 로그가 기록되고 서버가 중단되지 않는다.

---

# 12. 향후 확장

* GitLab
* Jenkins
* Azure DevOps
* Notion
* Slack
* Microsoft Teams
* AI 변경사항 요약
* 사용자별 알림 필터
* 관리자 웹페이지
* 프로젝트 대시보드
* 통계 리포트
* Slash Command
* 다중 Discord Server 지원
