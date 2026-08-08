# DisHost 배포 가이드

CollabNotify는 `dishost.py` 하나로 데이터베이스 마이그레이션, ngrok 터널,
FastAPI webhook 서버와 Discord 봇을 함께 실행한다. SQLite 데이터는
`/home/container/data/collabnotify.db`에 저장되어 서버 재시작 후에도 유지된다.

## 1. DisHost 서버 준비

- Python 3.12 서버를 만든다.
- 메모리는 최소 256MB, 권장 512MB 이상으로 선택한다.
- GitHub 저장소 파일을 `/home/container`에 업로드한다.
- 패널의 Startup File을 `dishost.py`로 지정한다.

패널에서 셸 명령을 설정할 수 있다면 다음과 같이 사용한다.

```sh
python dishost.py
```

## 2. 환경변수

`.env.example`을 `.env`로 복사하고 기존 Discord/Confluence 값을 채운 뒤 아래
값을 추가한다. `.env`는 GitHub에 커밋하지 않는다.

```dotenv
DISHOST_PORT=패널의_주_Allocation_포트
DISHOST_DATA_DIR=/home/container/data
NGROK_BIN=/home/container/data/ngrok/ngrok
NGROK_AUTHTOKEN=ngrok_대시보드의_토큰
NGROK_DOMAIN=할당받은이름.ngrok-free.app
```

`NGROK_AUTHTOKEN`과 `NGROK_DOMAIN`은 반드시 함께 설정한다. `pyngrok`이 첫
실행 때 공식 ngrok agent를 내려받아 영구 데이터 경로에 보관한다.

## 3. ngrok 무료 고정 주소

ngrok Dashboard의 **Domains**에서 무료 static domain을 하나 만든다. 표시된
호스트명만 `NGROK_DOMAIN`에 입력한다. `https://`는 넣지 않는다.

Confluence webhook URL은 다음과 같다.

```text
https://할당받은이름.ngrok-free.app/api/v1/webhook/confluence
```

GitHub와 Jira webhook도 같은 도메인의 해당 endpoint를 사용한다.

## 4. 첫 실행과 확인

서버 콘솔에서 아래 순서가 보이면 정상이다.

1. Alembic 데이터베이스 마이그레이션 완료
2. ngrok static domain 터널 시작
3. `CollabNotify API started.`
4. `Discord client is ready.`

다음 URL이 JSON 응답을 반환하는지 확인한다.

```text
https://할당받은이름.ngrok-free.app/health
```

환경변수를 바꾸었다면 서버를 완전히 재시작한다. 무료 DisHost 플랜은 서비스
유지를 위해 정기적인 수동 연장이 필요할 수 있으므로 대시보드의 만료일도
확인한다.
