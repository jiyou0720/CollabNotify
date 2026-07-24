"""Jira webhook event normalization."""

from collections.abc import Mapping

from app.core.enums import ServiceType
from app.core.exceptions import PayloadValidationError
from app.handlers.base_handler import BaseHandler, Payload
from app.schemas.common import Notification


class JiraHandler(BaseHandler):
    """Normalize supported Jira issue and comment events."""

    service = ServiceType.JIRA

    def parse(self, payload: Payload) -> Notification:
        """Parse Jira issue or comment payloads."""
        if self.event_type.startswith("comment_"):
            return self._parse_comment(payload)
        if self.event_type.startswith("jira:issue_"):
            return self._parse_issue(payload)
        raise PayloadValidationError(
            f"Unsupported Jira Handler event: {self.event_type}."
        )

    def _parse_issue(self, payload: Payload) -> Notification:
        issue = self.require_mapping(payload, "issue")
        fields = self.require_mapping(issue, "fields")
        issue_key = str(issue.get("key", "알 수 없음"))
        action = {
            "jira:issue_created": "생성",
            "jira:issue_updated": "수정",
            "jira:issue_deleted": "삭제",
        }[self.event_type]
        changes = self._format_changes(payload)
        description = (
            changes
            if changes
            else str(fields.get("summary", "Jira 이슈가 변경되었습니다."))
        )
        status_name = self.get_path(fields, "status", "name", default="알 수 없음")
        review_action = "OPEN"
        if self.event_type == "jira:issue_deleted" or str(status_name).lower() in {
            "done",
            "closed",
            "완료",
        }:
            review_action = "CLOSE"
        return self.build_notification(
            title=f"이슈 {action}",
            description=description,
            fields=[
                (
                    "프로젝트",
                    self.get_path(fields, "project", "name", default="알 수 없음"),
                ),
                ("이슈", issue_key),
                ("제목", fields.get("summary", "알 수 없음")),
                ("보고자", self.user_name(fields.get("reporter"))),
                ("담당자", self.user_name(fields.get("assignee"))),
                (
                    "우선순위",
                    self.get_path(fields, "priority", "name", default="알 수 없음"),
                ),
                ("상태", status_name),
            ],
            url=self._issue_url(issue),
            action_label="이슈 열기",
            external_resource_id=issue_key,
            review_action=review_action,
            review_thread_title=f"🧵 {issue_key} 토론",
        )

    def _parse_comment(self, payload: Payload) -> Notification:
        issue = self.require_mapping(payload, "issue")
        comment = self.require_mapping(payload, "comment")
        issue_fields = issue.get("fields", {})
        if not isinstance(issue_fields, Mapping):
            issue_fields = {}
        action = {
            "comment_created": "추가",
            "comment_updated": "수정",
            "comment_deleted": "삭제",
        }[self.event_type]
        return self.build_notification(
            title=f"댓글 {action}",
            description=str(comment.get("body", ""))[:300],
            fields=[
                (
                    "프로젝트",
                    self.get_path(
                        issue_fields, "project", "name", default="알 수 없음"
                    ),
                ),
                ("이슈", issue.get("key", "알 수 없음")),
                ("작성자", self.user_name(comment.get("author"))),
            ],
            url=self._issue_url(issue),
            action_label="이슈 열기",
        )

    @staticmethod
    def _format_changes(payload: Payload) -> str:
        changelog = payload.get("changelog")
        if not isinstance(changelog, Mapping):
            return ""
        items = changelog.get("items", [])
        if not isinstance(items, list):
            return ""
        changes = []
        for item in items:
            if not isinstance(item, Mapping):
                continue
            field = item.get("field", "항목")
            before = item.get("fromString", "없음")
            after = item.get("toString", "없음")
            changes.append(f"{field}: {before} → {after}")
        return "\n".join(changes)

    @staticmethod
    def _issue_url(issue: Mapping[str, object]) -> str | None:
        url = issue.get("self")
        return url if isinstance(url, str) and url else None
