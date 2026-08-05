"""Jira webhook event normalization."""

from collections.abc import Mapping

from app.core.enums import ServiceType
from app.core.exceptions import PayloadValidationError
from app.handlers.base_handler import BaseHandler, Payload
from app.schemas.common import Notification, NotificationActivity

TRACKED_CHANGE_FIELDS = frozenset(
    {
        "status",
        "assignee",
        "priority",
        "summary",
        "description",
        "labels",
        "resolution",
    }
)


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
        activities = self._issue_activities(payload)
        if self.event_type == "jira:issue_updated":
            self._logger.info(
                "Jira issue updated: issue=%s activity_count=%s",
                issue_key,
                len(activities),
            )
        if self.event_type == "jira:issue_deleted":
            activities = (
                NotificationActivity(
                    kind="issue_deleted", actor=self._event_actor(payload)
                ),
            )
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
            review_action=(
                "OPEN" if self.event_type == "jira:issue_created" else "APPEND"
            ),
            review_thread_title=f"🧵 {issue_key} 토론",
            activities=activities,
            parent_delivery=self.event_type == "jira:issue_created",
            parent_update=self.event_type != "jira:issue_created",
        )

    def _parse_comment(self, payload: Payload) -> Notification:
        issue_value = payload.get("issue", {})
        issue = issue_value if isinstance(issue_value, Mapping) else {}
        comment_value = payload.get("comment", {})
        comment = comment_value if isinstance(comment_value, Mapping) else {}
        issue_key = self._first_text(
            issue.get("key"), payload.get("issueKey"), payload.get("issue_key")
        )
        if issue_key is None:
            raise PayloadValidationError("Missing Jira issue key for comment event.")
        issue_fields = issue.get("fields", {})
        if not isinstance(issue_fields, Mapping):
            issue_fields = {}
        project_name = (
            self._first_text(
                self.get_path(issue_fields, "project", "name"),
                self.get_path(issue, "project", "name"),
                payload.get("projectName"),
                payload.get("projectKey"),
                self.get_path(payload, "project", "name"),
                self.get_path(payload, "project", "key"),
            )
            or "알 수 없음"
        )
        author = self._comment_author(payload, comment)
        body = self._comment_body(payload, comment)
        action = {
            "comment_created": "추가",
            "comment_updated": "수정",
            "comment_deleted": "삭제",
        }[self.event_type]
        ignored = self._ignore_comment(payload, comment)
        return self.build_notification(
            title=f"댓글 {action}",
            description=body[:300],
            fields=[
                (
                    "프로젝트",
                    project_name,
                ),
                ("이슈", issue_key),
                ("작성자", author),
            ],
            url=self._issue_url(issue) or self._first_text(payload.get("issueUrl")),
            action_label="이슈 열기",
            external_resource_id=issue_key,
            review_action="NONE" if ignored else "APPEND",
            activities=(
                (
                    NotificationActivity(
                        kind=self.event_type,
                        actor=author,
                        body=body[:1800],
                    ),
                )
                if not ignored
                else ()
            ),
            parent_delivery=False,
        )

    def _comment_author(self, payload: Payload, comment: Mapping[str, object]) -> str:
        """Resolve the real comment author from webhook or Automation fields."""
        for candidate in (
            comment.get("author"),
            payload.get("commentAuthor"),
            payload.get("author"),
            payload.get("user"),
            payload.get("initiator"),
        ):
            name = self.user_name(candidate)
            if name != "알 수 없음":
                return name
        return "알 수 없음"

    def _comment_body(self, payload: Payload, comment: Mapping[str, object]) -> str:
        """Resolve string or Atlassian Document Format comment content."""
        value = comment.get("body")
        if value is None:
            value = payload.get("commentBody", payload.get("body", ""))
        if isinstance(value, Mapping):
            text = self._adf_text(value)
            return text or str(value.get("text", ""))
        return str(value or "")

    @classmethod
    def _adf_text(cls, node: object) -> str:
        """Extract readable text recursively from Jira ADF."""
        if not isinstance(node, Mapping):
            return ""
        parts: list[str] = []
        text = node.get("text")
        if isinstance(text, str) and text:
            parts.append(text)
        content = node.get("content", [])
        if isinstance(content, list):
            for child in content:
                child_text = cls._adf_text(child)
                if child_text:
                    parts.append(child_text)
        separator = "\n" if node.get("type") == "doc" else ""
        return separator.join(parts)

    @staticmethod
    def _first_text(*values: object) -> str | None:
        """Return the first non-empty scalar string."""
        for value in values:
            if value is None or isinstance(value, Mapping):
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    def _ignore_comment(self, payload: Payload, comment: Mapping[str, object]) -> bool:
        """Reject issue-creation and automation-authored Jira comments."""
        event_name = str(payload.get("issue_event_type_name", "")).casefold()
        if (
            event_name in {"issue_created", "issue created"}
            or payload.get("isIssueCreation") is True
        ):
            self._logger.info("Jira issue-creation comment ignored.")
            return True
        author = comment.get("author")
        if not isinstance(author, Mapping):
            return False
        account_type = str(author.get("accountType", "")).casefold()
        identity = " ".join(
            str(author.get(field, ""))
            for field in (
                "displayName",
                "fullName",
                "publicName",
                "name",
                "username",
            )
        ).casefold()
        if account_type == "app" or any(
            marker in identity for marker in ("automation", "system", "bot")
        ):
            self._logger.info("Jira automation comment ignored: author=%s", identity)
            return True
        return False

    def _issue_activities(self, payload: Payload) -> tuple[NotificationActivity, ...]:
        """Normalize tracked changelog entries without Discord presentation logic."""
        changelog = payload.get("changelog")
        if not isinstance(changelog, Mapping):
            return ()
        items = changelog.get("items", [])
        if not isinstance(items, list):
            return ()
        actor = self._event_actor(payload)
        activities: list[NotificationActivity] = []
        for item in items:
            if not isinstance(item, Mapping):
                continue
            field = str(item.get("field", "")).strip().casefold()
            if field not in TRACKED_CHANGE_FIELDS:
                continue
            before = self._change_value(item.get("fromString"))
            after = self._change_value(item.get("toString"))
            if before == after:
                continue
            added: tuple[str, ...] = ()
            removed: tuple[str, ...] = ()
            if field == "labels":
                before_labels = self._labels(before)
                after_labels = self._labels(after)
                added = tuple(sorted(after_labels - before_labels))
                removed = tuple(sorted(before_labels - after_labels))
            activities.append(
                NotificationActivity(
                    kind=field,
                    before=before,
                    after=after,
                    actor=actor,
                    added=added,
                    removed=removed,
                )
            )
        return tuple(activities)

    def _event_actor(self, payload: Payload) -> str:
        """Extract the Jira user responsible for an issue activity."""
        return self.user_name(payload.get("user"))

    @staticmethod
    def _change_value(value: object) -> str:
        """Normalize absent Jira changelog values for presentation."""
        if value is None or str(value).strip() == "":
            return "없음"
        return str(value)

    @staticmethod
    def _labels(value: str) -> set[str]:
        """Parse Jira's comma-separated label changelog representation."""
        if value == "없음":
            return set()
        return {label.strip() for label in value.split(",") if label.strip()}

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
