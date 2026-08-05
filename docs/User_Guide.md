# User Guide

All visible bot text is Korean. Webhook notifications appear in the mapped
project channel with provider facts and a link to the original resource.

Eligible events automatically create a thread containing this review checklist:

- 요구사항 확인
- 구현 내용 검토
- 테스트 결과 확인
- 문서 업데이트 확인

Review state starts at `🟡 검토 중`. In the thread use `/review approve`,
`/review reject` (choose `수정 요청` or `반려`), `/review status`, or
`/review close`. Completion-producing provider events automatically post a
Korean completion message and archive the thread.

Use `/project list` to see project status and channels and `/project info` to
inspect category, mappings, and webhook readiness. Contact a server manager to
create, remap, archive, restore, or delete projects.

Example notification:

```text
🟣 PR 열림
저장소: collabnotify
작성자: 홍길동
[PR 열기]
```

Example review thread:

```text
🧵 PR #42 리뷰
📋 리뷰 체크리스트
□ 내용을 확인했습니다.
□ 피드백을 작성했습니다.
□ 승인 또는 수정 요청을 남겨주세요.
🟡 검토 중
```

## 외부 프로젝트 별칭 확인

`/project alias list`는 현재 Discord 서버의 GitHub, Jira, Confluence 외부
식별자와 내부 프로젝트 연결을 보여 줍니다. 목록에 없는 외부 프로젝트의 웹훅은
Discord 메시지를 만들지 않으므로 서버 관리자에게 별칭 등록을 요청하세요.

## Jira 활동 기록 보기

Jira 이슈의 리뷰 스레드에는 이슈 생성 이후의 주요 변경과 댓글 기록이 순서대로
표시됩니다. changelog 한 건에 여러 필드가 변경되면 각 변경이 별도 메시지로
표시됩니다. 완료된 이슈의 스레드는 자동 보관되며, 이슈를 다시 열면 같은 스레드가
복원되므로 이전 논의와 변경 이력을 계속 확인할 수 있습니다.

## GitHub PR 활동 기록 보기

GitHub PR 리뷰 스레드는 PR 하나의 전체 협업 기록을 제공합니다. 새 commit push,
리뷰 요청, 승인·변경 요청, 리뷰 댓글, 일반 댓글, 라벨·담당자 변경을 같은 곳에서
확인할 수 있습니다. 여러 commit push는 알림 과다 발생을 막기 위해 하나의 요약으로
표시됩니다.

PR이 종료되거나 merge되면 부모 GitHub 채널에 최종 결과가 표시되고 리뷰 스레드는
보관됩니다. PR을 다시 열면 기존 스레드가 복원되므로 이전 리뷰 기록을 잃지 않고
작업을 계속할 수 있습니다.
## 공통 협업 방식

GitHub PR, Jira Issue, Confluence Page마다 부모 embed와 활동 thread가 하나씩
제공됩니다. 부모 embed에서는 현재 상태를 확인하고, thread에서는 댓글·변경·push·
첨부파일 등 전체 활동 이력을 확인합니다. 후속 활동 때문에 부모 채널에 반복 메시지가
쌓이지 않으며, 보관 후 재개해도 기존 thread 기록이 유지됩니다.

## Confluence 문서 활동 보기

문서 생성 Embed에서 스페이스, 제목, 작성자, 생성 시각, 버전과 원문 링크를 확인할
수 있습니다. 연결된 Thread에는 수정자·수정 시각·버전 변경, 댓글 작성자와 내용,
첨부파일명과 업로더가 시간순으로 표시됩니다. 문서가 삭제되면 삭제 안내가 마지막에
추가되고 Thread가 자동 보관됩니다. 수정·댓글·첨부 이벤트 때문에 새 Thread가 생기지
않습니다.
