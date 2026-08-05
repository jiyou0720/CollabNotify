# Discord Bot Guide

Create a bot in the Discord Developer Portal, invite it with `bot` and
`applications.commands` scopes, and grant View Channels, Manage Channels,
Send Messages, Create Public Threads, Send Messages in Threads, Manage Threads,
Embed Links, and Read Message History. Configure `DISCORD_TOKEN` and optionally
`DISCORD_GUILD_ID`; the latter enables fast guild-scoped command synchronization.

The client uses only the guild intent. It does not require message, privileged
message-content, member, or presence intents. Startup registers project, review, admin,
settings, and test command groups. Shutdown closes the Gateway client cleanly on
SIGINT/SIGTERM or application lifespan termination.

Never publish the bot token. Rotate it immediately if exposed. Keep bot roles
below channels/categories it must manage. User-facing command descriptions,
responses, embeds, buttons, checklists, errors, and thread messages are Korean;
class names, logs, schemas, and APIs remain English.

## `/project alias` 명령

- `/project alias add provider external_name project_name`: 외부 식별자를 내부
  Discord 프로젝트에 연결합니다.
- `/project alias remove provider external_name`: 현재 서버 소유의 별칭을 삭제합니다.
- `/project alias list`: 현재 서버의 모든 별칭을 표시합니다.

세 명령은 서버 관리자 전용이며 응답은 요청자에게만 표시됩니다. 기존 `/project map`
및 `/project unmap` 명령은 별칭 명령으로 대체되었습니다. provider별 알림 채널은
프로젝트 생성 시 만들어진 `github`, `jira`, `confluence` 채널을 사용합니다.

## Jira 리뷰 스레드 타임라인

Jira 이슈 생성 알림에서 만들어진 `🧵 <이슈 키> 토론` 스레드는 이후 활동에도
계속 사용됩니다. 상태·담당자·우선순위 등 changelog의 각 변경은 별도 한국어
메시지로 게시되고 댓글 생성·수정·삭제도 같은 스레드에 기록됩니다.

이슈가 완료되면 `✅ 작업이 완료되었습니다.` 메시지와 함께 스레드가 보관됩니다.
완료된 이슈가 다시 열리면 동일 스레드가 자동으로 복원되고
`♻️ 작업이 다시 진행됩니다.` 메시지가 게시됩니다. 기존 매핑이 없는 활동은 중복
스레드 방지를 위해 표시되지 않습니다.

## GitHub PR 리뷰 스레드 타임라인

PR open 시 `#github` 채널에 rich embed를 게시하고 여기서 만든
`🧵 PR #번호 리뷰` 스레드 하나에 이후 활동을 누적합니다. 후속 이벤트는 새 부모
메시지를 만들지 않고 기존 embed만 최신 상태로 수정합니다.
리뷰 승인, 변경 요청, 리뷰 댓글, 일반 PR 댓글, 새 push, 리뷰어·라벨·담당자 변경,
Draft 및 리뷰 준비 상태가 모두 한국어로 표시됩니다. 여러 commit이 포함된 push도
한 개의 요약 메시지만 사용합니다.

merge되지 않은 PR 종료는 기존 부모 embed를 `🔒 PR 종료`, merge는
`✅ PR 병합`으로 수정합니다. 완료 후 스레드는 자동 보관됩니다. PR이 reopened되면
기존 스레드가 다시 열리며 새 스레드를 만들지 않습니다. 매핑된 리뷰 스레드가 없는
후속 이벤트는 중복 방지를 위해 경고만 기록하고 생략합니다.
## 공통 부모 embed 정책

GitHub PR, Jira Issue, Confluence Page의 부모 채널에는 객체별 embed가 하나만
존재합니다. 상태가 바뀌면 해당 embed가 수정되고, 활동 이력은 thread 안에서만
시간순으로 누적됩니다. 완료된 thread는 보관되고 재개 이벤트가 오면 동일 thread가
복원됩니다.

## Confluence 문서 Thread

문서 생성 Embed에서만 `🧵 <문서 제목> 리뷰` Thread를 만듭니다. 수정은
`📝 문서 수정`, 댓글은 `💬 새 댓글`, 첨부파일은 `📎 첨부파일 추가` 형식으로 기존
Thread에 게시됩니다. 문서 삭제 시 `🗑 문서가 삭제되었습니다.`를 게시하고 Manage
Threads 권한으로 자동 보관합니다. Page ID에 연결된 Thread가 없으면 안전하게
생략하므로 중복 Thread가 생성되지 않습니다.

리뷰 체크리스트는 부모 채널 메시지가 아니라 문서 생성 Embed에 연결된 Thread의 첫
메시지로 게시됩니다. 수정·댓글·첨부파일 활동은 모두 이 체크리스트 아래에 누적됩니다.
