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
