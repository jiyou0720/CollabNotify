# Webhook Guide

Public base URL examples:

- GitHub: `https://notify.example.com/api/v1/webhook/github`
- Jira: `https://notify.example.com/api/v1/webhook/jira`
- Confluence: `https://notify.example.com/api/v1/webhook/confluence`

Set GitHub content type to JSON and use the same secret as
`GITHUB_WEBHOOK_SECRET`; the server validates the exact raw body with
`X-Hub-Signature-256`. Configure Jira and Confluence to send the secret in
`X-Webhook-Secret`. Their values must match the corresponding environment
variables. Always use HTTPS.

Supported review-opening families are GitHub issue opened, pull request opened,
release created, failed workflow; Jira issue created/updated/assigned; and
Confluence page created/updated/deleted, comment added, attachment added. GitHub
merged or closed resources, Jira Done/Closed events, and Confluence page deletion
complete matching review threads.

Use unique delivery/request IDs. A 202 means the authenticated event is not
handled; a repeated ID is acknowledged without duplicate delivery. For 401,
check the selected secret and proxy body/header preservation. For 400, verify
JSON object shape and required event field/header. For 5xx, correlate structured
logs and `error_logs`; provider retries are safe when IDs remain stable.

```text
Provider -> HTTPS endpoint -> authenticate -> deduplicate -> normalize event
         -> resolve project/channel -> Korean Discord embed -> optional thread
```

## 웹훅 별칭 라우팅

실제 provider 설정 전에 Discord에서 외부 식별자를 등록해야 합니다.

| Provider | 등록할 `external_name` | Payload 원본 |
| --- | --- | --- |
| GitHub | `organization/repository` | `repository.full_name` |
| Jira | Jira 프로젝트명 | `issue.fields.project.name` |
| Confluence | Confluence 공간명 | `space.name` |

웹훅 수신 후 handler가 알림을 정규화하고, `ProjectAliasService`가 외부 식별자를
내부 프로젝트 ID로 변환합니다. 이후 해당 프로젝트의 provider 채널로 전달됩니다.
별칭이 없으면 요청 처리는 유지되지만 Discord 전송은 생략되고 경고 로그가 남습니다.

## Jira 활동 타임라인

다음 Jira 이벤트는 이슈 키에 연결된 기존 리뷰 스레드에 기록됩니다.

- `jira:issue_updated`: 상태, 담당자, 우선순위, 제목, 설명, 라벨, 해결 상태
- `jira:issue_deleted`: 이슈 삭제
- `comment_created`: 새 댓글
- `comment_updated`: 댓글 수정
- `comment_deleted`: 댓글 삭제

`jira:issue_created`만 리뷰 스레드를 생성합니다. 업데이트나 댓글 수신 시 기존
`ReviewThread` 매핑이 없으면 새 스레드를 만들지 않고 `Review thread missing` 경고를
남깁니다. `jira:issue_updated` payload에는 변경별 메시지를 만들 수 있도록
`changelog.items[].field`, `fromString`, `toString`을 포함해야 합니다.

동일 이벤트 재전송 방지를 위해 Jira Automation의 `X-Request-ID`에 실행별 고유값을
설정합니다. 같은 ID로 다시 수신된 요청은 Discord 채널과 타임라인에 중복 전송되지
않습니다.

Jira "Issue commented" Automation은 다음 본문을 권장합니다. 서버는 이 값을 사용해
`issueKey`와 동일한 `review_threads.external_resource_id`를 조회하며 부모 Embed나 새
Thread를 만들지 않습니다.

```json
{
  "webhookEvent": "comment_created",
  "issueKey": "{{issue.key}}",
  "projectName": "{{issue.project.name}}",
  "issueUrl": "{{issue.url}}",
  "commentAuthor": "{{comment.author.displayName}}",
  "commentBody": {{comment.body.asJsonString}}
}
```

Native Jira webhook의 `issue.key`, `issue.fields.project.name`,
`comment.author.displayName`, `comment.body` 구조도 동일하게 지원합니다. 댓글 본문이
ADF 객체이면 일반 텍스트로 변환합니다.

## GitHub PR 활동 타임라인

GitHub repository webhook에서 다음 이벤트를 활성화합니다.

- Pull requests
- Pull request reviews
- Pull request review comments
- Issue comments

지원 PR action은 `opened`, `edited`, `synchronize`, `reopened`,
`ready_for_review`, `converted_to_draft`, `review_requested`,
`review_request_removed`, `labeled`, `unlabeled`, `assigned`, `unassigned`,
`locked`, `unlocked`, `closed`입니다. GitHub의 merge는 `action=closed`와
`pull_request.merged=true` 조합으로 식별합니다.

PR의 일반 댓글은 `issue_comment` payload의 `issue.pull_request`가 존재할 때만 PR
타임라인으로 전달합니다. 일반 GitHub issue 댓글의 기존 동작은 유지됩니다. 인라인
리뷰 댓글은 `pull_request_review_comment` 이벤트로 처리합니다.

모든 요청에는 GitHub가 생성한 `X-GitHub-Delivery`가 포함되어야 합니다. 동일한
delivery ID는 audit log의 유일 제약으로 차단되어 부모 채널과 스레드 양쪽에서 중복
게시되지 않습니다. `synchronize` payload에 `commits` 목록이 있으면 짧은 SHA,
작성자, 메시지 첫 줄을 한 메시지로 요약합니다.
## Provider 공통 lifecycle

- GitHub `pull_request/opened`, Jira `jira:issue_created`, Confluence
  `page_created`는 부모 embed와 thread를 한 번만 생성합니다.
- GitHub PR 상태 변경, Jira issue update, Confluence page update는 기존 부모
  embed를 수정합니다.
- push, review, comment, attachment 활동은 부모 채널에 새 메시지를 만들지 않고
  기존 thread에만 기록합니다.
- 매핑이 없는 후속 이벤트는 새 thread를 만들지 않고 경고 후 생략합니다.

Jira `comment_created` 중 `author.accountType=app`, 작성자명에 automation/system/bot이
포함된 댓글, `issue_event_type_name=issue_created`로 표시된 생성 자동 댓글은 timeline에
추가하지 않습니다.

## Confluence Automation 요청

Automation의 "Send web request"에서 `POST`, `Content-Type: application/json`,
`X-Webhook-Secret: <CONFLUENCE_WEBHOOK_SECRET>`을 설정합니다. 중복 방지를 위해
`X-Request-ID`에는 실행마다 달라지는 Automation audit ID를 권장합니다. 서버는
`page_created`, `page_updated`, `comment_created`, `attachment_created`,
`page_deleted`를 지원합니다.

Confluence 공식 Automation smart value는 사용자 이름에 `fullName`/`publicName`,
페이지 시간에 `dateFirstPublished`/`dateLastUpdated`를 사용합니다. 생성·수정·삭제의
권장 본문은 다음 구조입니다. `version`과 `previousVersion`은 현재 Automation 규칙에서
사용 가능한 버전 값을 전달합니다.

```json
{
  "eventType": "page_updated",
  "page": {
    "id": "{{page.id}}",
    "title": "{{page.title}}",
    "url": "{{page.url}}",
    "author": {
      "fullName": "{{page.author.fullName}}",
      "publicName": "{{page.author.publicName}}"
    },
    "editor": {
      "fullName": "{{page.editor.fullName}}",
      "publicName": "{{page.editor.publicName}}"
    },
    "createdAt": "{{page.dateFirstPublished}}",
    "updatedAt": "{{page.dateLastUpdated}}",
    "version": "{{page.version}}"
  },
  "version": "{{page.version}}",
  "previousVersion": "{{previousVersion}}",
  "previousTitle": "{{previousTitle}}",
  "space": {"name": "{{space.name}}", "key": "{{space.key}}"},
  "initiator": {
    "fullName": "{{initiator.fullName}}",
    "publicName": "{{initiator.publicName}}"
  },
  "createdAt": "{{page.dateFirstPublished}}",
  "updatedAt": "{{page.dateLastUpdated}}",
  "timestamp": "{{now}}"
}
```

댓글은 `comment.body`(문자열 또는 `body.storage.value`)와 `page.id`, 첨부파일은
`attachment.title`, `attachment.fileSize`, `page.id`를 포함해야 합니다. 모든 후속
이벤트에서 최초 생성과 동일한 Page ID를 보내야 같은 Thread가 선택됩니다. Native
Confluence webhook의 `content`, `actor`, `version.by`, `version.when` 구조도 지원합니다.
Native Confluence webhook의 숫자형 `page.version`, `creationDate`,
`modificationDate`, `creatorAccountId`, `lastModifierAccountId`, `spaceKey`도 지원하며,
epoch millisecond 날짜는 ISO 8601 UTC 문자열로 변환합니다. 이름이 전달되면 account
ID보다 이름을 우선 표시하고, 모든 지원 경로가 비어 있을 때만 `알 수 없음`을 표시합니다.
