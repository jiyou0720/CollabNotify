# 01. Project Overview

# CollabNotify

> Jira · Confluence · GitHub 통합 Discord 알림 시스템

Version: 1.0
Author: 박지유
Status: Draft

---

# 1. 프로젝트 소개

CollabNotify는 Jira, Confluence, GitHub에서 발생하는 다양한 협업 이벤트를 하나의 Discord 서버로 실시간 전달하는 디스코드 봇 통합 알림 시스템이다.

기존에는 개발자와 팀원이 Jira, Confluence, GitHub를 각각 접속하여 변경 사항을 확인해야 했으며, 중요한 이벤트를 놓치는 경우가 발생했다.

CollabNotify는 이러한 문제를 해결하기 위해 각 협업 도구의 Webhook을 수신하고 Discord Bot을 통해 보기 쉬운 형태의 Embed 메시지로 전달한다.

이를 통해 프로젝트 진행 상황을 Discord 하나만으로도 빠르게 확인할 수 있으며, 팀원 간의 협업 효율을 향상시키는 것을 목표로 한다.

---

# 2. 개발 목적

본 프로젝트의 목적은 다음과 같다.

* Jira, Confluence, GitHub의 이벤트를 하나의 플랫폼에서 통합 관리
* Discord 기반 실시간 협업 알림 제공
* 협업 도구를 자주 방문하지 않아도 프로젝트 진행 상황 파악 가능
* 프로젝트 변경 사항을 즉시 공유하여 의사소통 비용 감소
* 확장 가능한 구조를 설계하여 다양한 협업 도구 연동 지원

---

# 3. 프로젝트 목표

## Functional Goals

* Jira 이벤트 실시간 수신
* Confluence 이벤트 실시간 수신
* GitHub 이벤트 실시간 수신
* Discord Embed 메시지 전송
* Discord 버튼을 통한 원본 페이지 이동
* 이벤트 종류별 채널 분리
* Webhook Secret 검증
* 비동기 처리 기반의 안정적인 이벤트 처리

---

## Non-Functional Goals

* 높은 유지보수성
* 모듈화된 구조
* 쉬운 확장성
* 안정적인 예외 처리
* 빠른 이벤트 처리 속도
* Discord API Rate Limit 대응

---

# 4. 주요 기능

## Jira

* Issue 생성
* Issue 수정
* Issue 삭제
* 담당자 변경
* 상태 변경
* 우선순위 변경
* 댓글 작성

---

## Confluence

* 문서 생성
* 문서 수정
* 댓글 작성
* 첨부파일 업로드

---

## GitHub

* Issue 생성
* Issue 종료
* Issue 재오픈
* Pull Request 생성
* Pull Request Review
* Pull Request Merge
* Push
* Release 생성
* Tag 생성
* Branch 생성/삭제
* GitHub Actions 실행 결과

---

## Discord

* Embed 메시지
* 버튼(Button)
* 링크 이동
* 채널 분리
* 색상 구분
* Timestamp 표시

---

# 5. 시스템 개요

```
Jira ───────────────┐
                    │
Confluence ─────────┼────► FastAPI Webhook Server
                    │
GitHub ─────────────┘
                             │
                             ▼
                    Event Dispatcher
                             │
             ┌───────────────┼───────────────┐
             │               │               │
        Jira Handler   GitHub Handler   Confluence Handler
             │               │               │
             └───────────────┼───────────────┘
                             ▼
                     Discord Service
                             │
                             ▼
                       Discord Bot
                             │
                             ▼
                      Discord Server
```

---

# 6. 개발 환경

## Backend

* Python 3.12
* FastAPI
* Uvicorn
* discord.py
* httpx
* python-dotenv
* Pydantic

---

## Database

초기 버전

* SQLite

확장 버전

* PostgreSQL

---

## Version Control

* Git
* GitHub

---

## IDE

* Visual Studio Code

---

## Deployment

* Local Windows
* Ubuntu
* Docker
* Docker Compose

---

# 7. 주요 사용자

## 관리자(Admin)

* Webhook 설정
* Discord Bot 설정
* 채널 관리
* 프로젝트 설정

---

## 개발자(Developer)

* GitHub 이벤트 확인
* Jira 이벤트 확인
* PR 진행 상황 확인

---

## 기획자(Project Manager)

* Jira 진행 상황 확인
* Confluence 문서 변경 확인
* 프로젝트 일정 관리

---

## 팀원(Member)

* 프로젝트 변경 사항 확인
* 문서 변경 사항 확인
* 개발 진행 상황 확인

---

# 8. 프로젝트 특징

### 통합 알림

여러 협업 도구를 하나의 Discord 서버에서 확인할 수 있다.

### 실시간 처리

Webhook 기반으로 이벤트를 즉시 처리한다.

### 직관적인 UI

Discord Embed를 이용하여 정보를 보기 쉽게 제공한다.

### 버튼 지원

Discord에서 바로 원본 페이지(Jira, Confluence, GitHub)로 이동할 수 있다.

### 모듈화

새로운 협업 도구를 추가할 때 Handler만 구현하면 쉽게 확장 가능하다.

---

# 9. 개발 범위

본 프로젝트에서 개발하는 기능

* Discord Bot
* FastAPI Webhook Server
* Jira 연동
* Confluence 연동
* GitHub 연동
* Discord Embed UI
* Webhook Secret 검증
* 로그 시스템
* 환경 변수 관리

---

본 프로젝트 범위에 포함하지 않는 기능

* Jira 데이터 수정
* GitHub API를 통한 Repository 관리
* Confluence 문서 편집
* 사용자 인증(OAuth)
* 웹 관리자 페이지
* 모바일 애플리케이션

---

# 10. 기대 효과

* 협업 도구 확인 시간을 줄일 수 있다.
* 프로젝트 진행 상황을 실시간으로 공유할 수 있다.
* 중요한 이벤트를 놓치는 일을 최소화할 수 있다.
* 팀원 간 커뮤니케이션 효율이 향상된다.
* 하나의 플랫폼에서 프로젝트 상태를 통합적으로 확인할 수 있다.

---

# 11. 향후 확장 계획

* GitLab 연동
* Jenkins 연동
* Azure DevOps 연동
* Slack 연동
* Microsoft Teams 연동
* Notion 연동
* 사용자별 알림 설정
* Discord Slash Command
* AI 기반 변경 사항 요약
* 웹 관리 페이지
* 통계 및 대시보드

---

# 12. 문서 구성

본 프로젝트는 다음 문서를 기준으로 개발을 진행한다.

| 문서                     | 설명               |
| ---------------------- | ---------------- |
| 01_Project_Overview    | 프로젝트 개요          |
| 02_PRD                 | 제품 요구사항 명세       |
| 03_System_Architecture | 시스템 아키텍처         |
| 04_API_Specification   | API 및 Webhook 명세 |
| 05_Discord_UI_Guide    | Discord UI 가이드   |
| 06_Database_Design     | 데이터베이스 설계        |
| 07_Project_Structure   | 프로젝트 구조          |
| 08_Class_Design        | 클래스 설계           |
| 09_Development_Guide   | 개발 가이드           |
| 10_TODO                | 개발 체크리스트         |
| 11_Deployment          | 배포 가이드           |
| 12_Test_Cases          | 테스트 시나리오         |
| 13_Future_Features     | 향후 확장 기능         |
