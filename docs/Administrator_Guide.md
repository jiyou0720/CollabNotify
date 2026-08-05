# Administrator Guide

Commands that mutate projects or system settings require Discord Administrator
or Manage Server permission.

- `/project create|delete|archive|restore|list|info|map|unmap`
- `/admin sync|cleanup|status`
- `/settings reviewers|notifications|archive-days|auto-thread`
- `/test github|jira|confluence`

Project creation builds one category and six channels and writes default
provider mappings. Deletion requires an explicit button confirmation and removes
Discord resources and dependent database configuration. Archive disables
notifications and moves channels under `📦 Archived`; restore recreates the
category association and enables delivery.

Run `/admin sync` after command deployment, `/admin cleanup` after manual Discord
channel deletion, and `/admin status` for database, project, open-review, and
Gateway latency checks. Configure auto-archive to 1, 3, or 7 days. Use test
commands after mapping changes; they send Korean preview embeds only.

Operational alerts should monitor application exit, repeated webhook 5xx,
database write errors, Discord rate limiting, and growing `error_logs` volume.

## Server management workflow

```text
/project create -> Discord resources -> database project/mappings -> success
/project archive -> move channels -> disable notifications
/project restore -> restore category -> enable notifications
/project delete -> confirmation -> delete resources -> cascade configuration
```

## Permissions

All `/project`, `/admin`, `/settings`, and `/test` commands require either
Administrator or Manage Server. `/review close` has the same restriction;
review participants may use approve, reject, and status inside registered threads.
Discord channel permissions still govern visibility and message/thread access.

## 외부 프로젝트 별칭 관리

프로젝트를 만든 뒤 provider별 웹훅 식별자를 등록합니다. 내부 프로젝트명에는 외부
서비스 이름을 사용할 필요가 없습니다.

```text
/project alias add provider:GitHub external_name:organization/repository project_name:내부 프로젝트명
/project alias add provider:Jira external_name:프로젝트명 project_name:내부 프로젝트명
/project alias add provider:Confluence external_name:공간명 project_name:내부 프로젝트명
/project alias list
/project alias remove provider:GitHub external_name:organization/repository
```

서로 다른 provider의 여러 외부 프로젝트를 같은 내부 프로젝트에 연결할 수 있습니다.
동일한 provider와 외부 식별자의 중복 등록은 거부됩니다. 별칭 미등록 경고는
`Project alias not configured` 로그로 찾을 수 있습니다.

## Jira Activity Timeline 운영

Jira Automation에서 이슈 생성, 수정, 삭제 및 댓글 생성·수정·삭제 이벤트를 전송해야
합니다. 수정 이벤트에는 `changelog.items`가 있어야 상태, 담당자, 우선순위, 제목,
설명, 라벨, 해결 상태의 이전 값과 새 값을 기록할 수 있습니다.

운영 로그에서 다음 항목을 확인할 수 있습니다.

- `Jira issue updated`: 감지한 변경 수
- `Review thread found`: 이슈 키에 연결된 스레드
- `Jira status changed`: 상태 변경 게시
- `Jira review thread archived`: 완료 후 보관
- `Jira review thread reopened`: 재개 후 복원
- `Jira comment activity appended`: 댓글 활동 게시
- `Review thread missing`: 기존 매핑이 없어 안전하게 생략한 활동

중복 활동을 막으려면 Jira Automation의 `X-Request-ID` 헤더에 각 Automation 실행의
고유 식별자를 전달하십시오.

## GitHub PR Activity Timeline 운영

GitHub repository webhook에서 Pull requests, Pull request reviews, Pull request
review comments, Issue comments 이벤트를 선택합니다. webhook endpoint와 secret은
기존 GitHub 설정을 그대로 사용하며 `X-GitHub-Delivery`는 GitHub가 자동으로
전달합니다.

정상 운영 시 다음 구조화 로그를 확인할 수 있습니다.

- `GitHub PR opened`: 최초 PR 스레드 요약
- `GitHub commit received`: synchronize commit 요약
- `GitHub review received`: 승인·변경 요청·리뷰 변경
- `GitHub comment received`: PR 일반 댓글
- `Review thread archived`: PR 종료 또는 merge
- `Review thread reopened`: reopened PR
- `Review thread missing`: PR 후속 이벤트에 대응하는 기존 스레드 없음

후속 이벤트가 부모 채널에는 보이지 않고 리뷰 스레드에만 나타나는 것이 정상입니다.
PR open은 부모 GitHub 채널에 rich embed 하나를 생성합니다. 이후 상태 변경은 새
부모 메시지를 만들지 않고 이 embed를 수정하며, 활동 기록은 연결된 thread에만
추가됩니다.
## Unified thread lifecycle 운영

부모 메시지 수정에는 봇의 `메시지 보기`, `메시지 기록 보기`, `메시지 보내기`
권한이 필요합니다. thread 생성·복원·보관에는 public thread 생성과 thread 관리
권한이 필요합니다.

정상 상태에서는 객체 하나마다 `review_threads` 행 하나만 존재하며
`discord_message_id`는 최신 상태를 표시하는 부모 embed, `discord_thread_id`는 활동
timeline을 가리킵니다. `Parent message update skipped` 경고는 과거 standalone
thread처럼 부모 메시지가 없는 legacy 데이터에서 발생할 수 있으며 timeline 처리는
계속됩니다.

## Confluence Timeline 운영

Confluence Automation마다 동일한 Page ID를 전송하고 `page_created`가 후속 이벤트보다
먼저 도착하도록 구성합니다. 생성 이벤트가 `review_threads`에 Page ID와 Thread ID를
저장하며, 수정·댓글·첨부·삭제는 이 매핑만 사용합니다. 매핑이 없으면
`Review thread missing: service=confluence` 경고를 남기고 새 Thread를 만들지 않습니다.
`page_deleted` 처리 후 행의 상태가 `COMPLETED`가 되고 Discord Thread가 보관됩니다.

Embed에 `알 수 없음`이 표시되면 Automation 본문에서 `page.author.fullName`,
`page.editor.fullName`, `page.dateFirstPublished`, `page.dateLastUpdated`, `version`을
확인하십시오. Confluence의 사용자 smart value는 Jira와 달리 `displayName`보다
`fullName`/`publicName`을 사용합니다. 정확한 수정 이력에는 `previousVersion`을 함께
전송해야 합니다. 전체 요청 예시는 Webhook Guide를 참조하십시오.
