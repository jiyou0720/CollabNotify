"""GitHub webhook event normalization."""

from collections.abc import Mapping
from typing import Any

from app.core.enums import ServiceType
from app.core.exceptions import PayloadValidationError, UnsupportedEventError
from app.handlers.base_handler import BaseHandler, Payload
from app.schemas.common import Notification


class GithubHandler(BaseHandler):
    """Normalize supported GitHub events."""

    service = ServiceType.GITHUB
    _ACTIONS = {
        "issues": {
            "opened",
            "edited",
            "closed",
            "reopened",
            "assigned",
            "unassigned",
            "labeled",
            "unlabeled",
        },
        "issue_comment": {"created", "edited", "deleted"},
        "pull_request": {
            "opened",
            "edited",
            "synchronize",
            "reopened",
            "closed",
            "ready_for_review",
            "converted_to_draft",
            "review_requested",
            "review_request_removed",
        },
        "pull_request_review": {"submitted", "edited", "dismissed"},
        "release": {
            "published",
            "unpublished",
            "created",
            "edited",
            "deleted",
            "prereleased",
            "released",
        },
        "workflow_run": {"requested", "completed"},
    }
    _ACTION_LABELS = {
        "opened": "생성",
        "edited": "수정",
        "closed": "종료",
        "reopened": "다시 열림",
        "assigned": "담당자 지정",
        "unassigned": "담당자 해제",
        "labeled": "라벨 추가",
        "unlabeled": "라벨 제거",
        "created": "작성",
        "deleted": "삭제",
        "synchronize": "동기화",
        "ready_for_review": "리뷰 준비",
        "converted_to_draft": "초안 전환",
        "review_requested": "리뷰 요청",
        "review_request_removed": "리뷰 요청 취소",
        "submitted": "제출",
        "dismissed": "해제",
        "published": "게시",
        "unpublished": "게시 취소",
        "prereleased": "사전 릴리스",
        "released": "릴리스",
        "requested": "요청",
        "completed": "완료",
    }

    def parse(self, payload: Payload) -> Notification:
        """Route a GitHub payload to its event-specific parser."""
        parsers = {
            "issues": self._parse_issue,
            "issue_comment": self._parse_issue_comment,
            "pull_request": self._parse_pull_request,
            "pull_request_review": self._parse_review,
            "push": self._parse_push,
            "release": self._parse_release,
            "workflow_run": self._parse_workflow,
            "create": self._parse_ref,
            "delete": self._parse_ref,
        }
        try:
            notification = parsers[self.event_type](payload)
        except KeyError as exc:
            raise PayloadValidationError(
                f"Unsupported GitHub Handler event: {self.event_type}."
            ) from exc
        self._validate_action(payload)
        return notification

    def _validate_action(self, payload: Payload) -> None:
        """Ignore provider actions excluded by the API specification."""
        supported = self._ACTIONS.get(self.event_type)
        if supported is None:
            return
        action = payload.get("action")
        if not isinstance(action, str) or action not in supported:
            raise UnsupportedEventError(
                f"Unsupported GitHub action: {self.event_type}/{action}."
            )

    def _repository(self, payload: Payload) -> str:
        repository = self.require_mapping(payload, "repository")
        name = repository.get("full_name") or repository.get("name")
        if not isinstance(name, str) or not name:
            raise PayloadValidationError("Missing GitHub repository name.")
        return name

    def _action(self, payload: Payload) -> str:
        action = str(payload.get("action", "updated"))
        return self._ACTION_LABELS.get(action, "변경")

    def _parse_issue(self, payload: Payload) -> Notification:
        issue = self.require_mapping(payload, "issue")
        repository = self._repository(payload)
        issue_number = issue.get("number", "알 수 없음")
        action = payload.get("action")
        labels = [
            label.get("name", "")
            for label in issue.get("labels", [])
            if isinstance(label, Mapping)
        ]
        return self.build_notification(
            title=f"이슈 {self._action(payload)}",
            description=str(issue.get("title", "GitHub 이슈가 변경되었습니다.")),
            fields=[
                ("저장소", repository),
                ("이슈", f"#{issue_number}"),
                ("작성자", self.user_name(issue.get("user"))),
                ("상태", issue.get("state", "알 수 없음")),
                ("라벨", labels),
            ],
            url=self._url(issue),
            action_label="이슈 열기",
            external_resource_id=f"{repository}:issue:{issue_number}",
            review_action=(
                "OPEN"
                if action == "opened"
                else "CLOSE" if action == "closed" else "NONE"
            ),
            review_thread_title=f"🧵 Issue #{issue_number} 토론",
        )

    def _parse_issue_comment(self, payload: Payload) -> Notification:
        issue = self.require_mapping(payload, "issue")
        comment = self.require_mapping(payload, "comment")
        return self.build_notification(
            title=f"이슈 댓글 {self._action(payload)}",
            description=str(comment.get("body", "")),
            fields=[
                ("저장소", self._repository(payload)),
                ("이슈", f"#{issue.get('number', '알 수 없음')}"),
                ("작성자", self.user_name(comment.get("user"))),
            ],
            url=self._url(comment),
            action_label="이슈 열기",
        )

    def _parse_pull_request(self, payload: Payload) -> Notification:
        pull_request = self.require_mapping(payload, "pull_request")
        repository = self._repository(payload)
        pr_number = pull_request.get("number", payload.get("number", "알 수 없음"))
        action = payload.get("action")
        merged = bool(pull_request.get("merged", False))
        return self.build_notification(
            title=f"PR {self._action(payload)}",
            description=str(pull_request.get("title", "PR이 변경되었습니다.")),
            fields=[
                ("저장소", repository),
                ("PR", f"#{pr_number}"),
                ("작성자", self.user_name(pull_request.get("user"))),
                (
                    "기준 브랜치",
                    self.get_path(pull_request, "base", "ref", default="알 수 없음"),
                ),
                (
                    "작업 브랜치",
                    self.get_path(pull_request, "head", "ref", default="알 수 없음"),
                ),
                ("병합 여부", pull_request.get("merged", False)),
            ],
            url=self._url(pull_request),
            action_label="PR 열기",
            external_resource_id=f"{repository}:pr:{pr_number}",
            review_action=(
                "OPEN"
                if action == "opened"
                else "CLOSE" if action == "closed" and merged else "NONE"
            ),
            review_thread_title=f"🧵 PR #{pr_number} 리뷰",
        )

    def _parse_review(self, payload: Payload) -> Notification:
        review = self.require_mapping(payload, "review")
        pull_request = self.require_mapping(payload, "pull_request")
        return self.build_notification(
            title=f"PR 리뷰 {self._action(payload)}",
            description=str(review.get("body", "리뷰가 변경되었습니다.")),
            fields=[
                ("저장소", self._repository(payload)),
                ("PR", f"#{pull_request.get('number', '알 수 없음')}"),
                ("리뷰어", self.user_name(review.get("user"))),
                ("상태", review.get("state", "알 수 없음")),
            ],
            url=self._url(review) or self._url(pull_request),
            action_label="PR 열기",
        )

    def _parse_push(self, payload: Payload) -> Notification:
        commits = payload.get("commits", [])
        if not isinstance(commits, list):
            raise PayloadValidationError("Invalid GitHub commits list.")
        branch = str(payload.get("ref", "알 수 없음")).removeprefix("refs/heads/")
        messages = [
            str(commit.get("message", ""))
            for commit in commits[:5]
            if isinstance(commit, Mapping) and commit.get("message")
        ]
        description = "\n".join(messages) or (
            f"{branch} 브랜치에 커밋 {len(commits)}개를 푸시했습니다."
        )
        return self.build_notification(
            title="코드 푸시",
            description=description,
            fields=[
                ("저장소", self._repository(payload)),
                ("브랜치", branch),
                ("커밋 수", len(commits)),
                ("작성자", self.user_name(payload.get("pusher"))),
            ],
            url=str(payload.get("compare", "")) or None,
            action_label="커밋 열기",
        )

    def _parse_release(self, payload: Payload) -> Notification:
        release = self.require_mapping(payload, "release")
        repository = self._repository(payload)
        version = release.get("tag_name", "알 수 없음")
        return self.build_notification(
            title=f"릴리스 {self._action(payload)}",
            description=str(release.get("name") or release.get("tag_name", "릴리스")),
            fields=[
                ("저장소", repository),
                ("버전", version),
                ("작성자", self.user_name(release.get("author"))),
            ],
            url=self._url(release),
            action_label="릴리스 열기",
            external_resource_id=f"{repository}:release:{version}",
            review_action=("OPEN" if payload.get("action") == "created" else "NONE"),
            review_thread_title=f"🧵 {version} 릴리스 리뷰",
        )

    def _parse_workflow(self, payload: Payload) -> Notification:
        workflow = self.require_mapping(payload, "workflow_run")
        repository = self._repository(payload)
        workflow_name = workflow.get("name", "알 수 없음")
        result = workflow.get("conclusion") or workflow.get("status", "알 수 없음")
        return self.build_notification(
            title=f"워크플로 {self._action(payload)}",
            description=str(workflow.get("name", "GitHub 워크플로가 변경되었습니다.")),
            fields=[
                ("저장소", repository),
                ("워크플로", workflow_name),
                ("브랜치", workflow.get("head_branch", "알 수 없음")),
                (
                    "결과",
                    result,
                ),
                ("커밋", workflow.get("head_sha", "알 수 없음")),
                ("실행 시간", self._workflow_duration(workflow)),
            ],
            url=self._url(workflow),
            action_label="워크플로 열기",
            external_resource_id=(
                f"{repository}:workflow:{workflow.get('id', workflow_name)}"
            ),
            review_action=(
                "OPEN"
                if payload.get("action") == "completed"
                and str(result).lower() == "failure"
                else "NONE"
            ),
            review_thread_title=f"🧵 {workflow_name} 실패 검토",
        )

    @staticmethod
    def _workflow_duration(workflow: Mapping[str, Any]) -> str:
        """Return provider duration data when supplied by GitHub."""
        return str(workflow.get("run_duration_ms", "알 수 없음"))

    def _parse_ref(self, payload: Payload) -> Notification:
        action = "생성" if self.event_type == "create" else "삭제"
        reference_type = payload.get("ref_type", "reference")
        reference = payload.get("ref", "")
        return self.build_notification(
            title=f"참조 {action}",
            description=f"{reference_type} {reference}",
            fields=[
                ("저장소", self._repository(payload)),
                ("종류", payload.get("ref_type", "알 수 없음")),
                ("참조", payload.get("ref", "알 수 없음")),
                ("작성자", self.user_name(payload.get("sender"))),
            ],
        )

    @staticmethod
    def _url(value: Mapping[str, Any]) -> str | None:
        url = value.get("html_url")
        return url if isinstance(url, str) and url else None
