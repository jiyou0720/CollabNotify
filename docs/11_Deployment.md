# 11_Deployment

# Deployment Guide

Project : CollabNotify
Version : 1.0
Status : Draft

---

# 1. 목적

본 문서는 CollabNotify의 운영 환경 배포 절차를 정의한다.

배포 목표

* 빠른 배포
* 안정적인 운영
* 자동 재시작
* 쉬운 업데이트
* 로그 관리
* 데이터 보존

본 프로젝트는 **Docker Compose 기반 단일 서버 배포**를 기본으로 한다.

---

# 2. 운영 환경

## 권장 서버

현재 프로젝트 기준

* Windows 11 또는 Ubuntu 22.04 이상이 설치된 노트북
* 항상 전원이 켜져 있는 환경
* 인터넷 연결 유지

향후 운영 환경

* VPS
* Cloud VM
* NAS
* Raspberry Pi 5

---

# 3. 기술 스택

| 항목            | 기술                                 |
| ------------- | ---------------------------------- |
| OS            | Ubuntu 22.04 LTS (권장) / Windows 11 |
| Runtime       | Python 3.12                        |
| Web Framework | FastAPI                            |
| Discord       | discord.py                         |
| Web Server    | Uvicorn                            |
| Reverse Proxy | Nginx (선택)                         |
| Database      | SQLite                             |
| Container     | Docker                             |
| Orchestration | Docker Compose                     |

---

# 4. 배포 구조

```text id="deploy_arch"
                GitHub
                  │
                  │ Webhook
                  ▼
            Internet
                  │
                  ▼
          Nginx (Optional)
                  │
                  ▼
        FastAPI (Docker)
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
 Discord Bot          SQLite Database
        │
        ▼
 Discord Server
```

---

# 5. 서버 요구사항

최소 사양

| 항목      | 권장      |
| ------- | ------- |
| CPU     | 2 Core  |
| Memory  | 4GB     |
| Storage | 20GB 이상 |
| Network | 항상 연결   |

---

# 6. 프로젝트 배치

```text id="deploy_dir"
/opt/collabnotify/

├── app/
├── database/
├── docs/
├── logs/
├── scripts/
├── .env
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

Windows의 경우

```text id="deploy_windows"
C:\CollabNotify\
```

---

# 7. 환경 변수

`.env`

```env id="deploy_env"
DISCORD_TOKEN=YOUR_DISCORD_TOKEN
DISCORD_GUILD_ID=YOUR_GUILD_ID

DATABASE_URL=sqlite:///database/collabnotify.db

LOG_LEVEL=INFO

GITHUB_WEBHOOK_SECRET=CHANGE_ME
JIRA_WEBHOOK_SECRET=CHANGE_ME
CONFLUENCE_WEBHOOK_SECRET=CHANGE_ME
```

주의

* `.env`는 Git에 포함하지 않는다.
* 운영 환경에서는 실제 Secret 값을 사용한다.

---

# 8. Dockerfile

```dockerfile id="dockerfile_example"
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

# 9. docker-compose.yml

```yaml id="compose_example"
services:
  collabnotify:
    build: .
    container_name: collabnotify

    restart: unless-stopped

    ports:
      - "8000:8000"

    env_file:
      - .env

    volumes:
      - ./database:/app/database
      - ./logs:/app/logs
```

---

# 10. 이미지 생성

```bash id="docker_build"
docker compose build
```

---

# 11. 컨테이너 실행

```bash id="docker_up"
docker compose up -d
```

확인

```bash id="docker_ps"
docker ps
```

---

# 12. 로그 확인

```bash id="docker_logs"
docker compose logs -f
```

특정 서비스

```bash id="docker_logs_service"
docker compose logs -f collabnotify
```

---

# 13. 서비스 중지

```bash id="docker_down"
docker compose down
```

---

# 14. 서비스 재시작

```bash id="docker_restart"
docker compose restart
```

---

# 15. 업데이트 절차

코드 가져오기

```bash id="git_pull"
git pull
```

재빌드

```bash id="docker_rebuild"
docker compose up -d --build
```

---

# 16. 데이터 백업

SQLite

```bash id="backup_sqlite"
cp database/collabnotify.db backup/collabnotify.db
```

로그

```bash id="backup_logs"
cp -r logs backup/
```

권장 주기

* Database : 하루 1회
* Logs : 주 1회

---

# 17. 복원

```bash id="restore_sqlite"
cp backup/collabnotify.db database/
```

컨테이너 재시작

```bash id="restart_after_restore"
docker compose restart
```

---

# 18. Nginx (선택)

Reverse Proxy 예시

```nginx id="nginx_example"
server {

    listen 80;

    server_name your-domain.com;

    location / {

        proxy_pass http://localhost:8000;

    }

}
```

---

# 19. HTTPS

권장

* Let's Encrypt
* Certbot

HTTPS 적용 후

```text id="https_url"
https://your-domain.com
```

Webhook URL도 HTTPS를 사용한다.

---

# 20. Discord Bot 운영

Bot은 항상 실행 상태를 유지해야 한다.

Docker의

```text id="restart_policy"
restart: unless-stopped
```

옵션을 사용한다.

---

# 21. 운영 체크리스트

배포 전

* [ ] `.env` 확인
* [ ] Secret 확인
* [ ] Docker Build 성공
* [ ] Database 생성
* [ ] 로그 디렉터리 생성

배포 후

* [ ] FastAPI 실행 확인
* [ ] Discord Bot 로그인 확인
* [ ] GitHub Webhook 테스트
* [ ] Jira Webhook 테스트
* [ ] Confluence Webhook 테스트

---

# 22. 장애 대응

## Discord API 오류

조치

* Token 확인
* Network 확인
* Rate Limit 확인

---

## SQLite 오류

조치

* Database 권한 확인
* Volume 확인

---

## Webhook 401

조치

* Secret 확인
* Signature 확인

---

## Container 종료

확인

```bash id="docker_logs_error"
docker compose logs
```

---

# 23. 모니터링

권장 항목

* CPU 사용률
* Memory 사용률
* Disk 사용량
* Docker 상태
* FastAPI 상태
* Discord 연결 상태

로그

```text id="monitor_logs"
logs/application.log

logs/error.log
```

---

# 24. 보안 권장사항

* Secret은 환경 변수로 관리한다.
* HTTPS를 사용한다.
* Git에 `.env`를 업로드하지 않는다.
* Webhook Signature를 검증한다.
* 운영 서버에는 최소 권한 원칙을 적용한다.
* 정기적으로 의존성을 업데이트한다.

---

# 25. 운영 유지보수

주간 작업

* 로그 확인
* 디스크 사용량 확인
* Docker 이미지 정리

월간 작업

* Python 패키지 업데이트
* 보안 패치 적용
* 데이터베이스 백업 검증

---

# 26. 향후 배포 확장

향후 지원 예정

* PostgreSQL
* Redis
* GitHub Actions 기반 CI/CD
* Kubernetes
* Helm Chart
* AWS ECS
* Azure Container Apps
* Google Cloud Run

---

# 27. 롤백 절차

1. 이전 Git Commit으로 복원

```bash id="rollback_git"
git checkout <commit_hash>
```

2. 이미지 재생성

```bash id="rollback_build"
docker compose up -d --build
```

3. 필요 시 데이터베이스 복원

```bash id="rollback_db"
cp backup/collabnotify.db database/
```

---

# 28. 완료 기준

다음 조건을 만족하면 배포가 완료된 것으로 판단한다.

* Docker 컨테이너가 정상 실행된다.
* FastAPI API가 정상 응답한다.
* Discord Bot이 정상 로그인된다.
* GitHub, Jira, Confluence Webhook이 정상 수신된다.
* 데이터베이스와 로그가 영속적으로 저장된다.
* 서비스 재시작 후에도 설정과 데이터가 유지된다.
* 운영 환경에서 안정적으로 24시간 이상 동작한다.
