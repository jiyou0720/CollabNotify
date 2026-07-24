"""Confluence webhook event normalization."""

from collections.abc import Mapping

from app.core.enums import ServiceType
from app.core.exceptions import PayloadValidationError
from app.handlers.base_handler import BaseHandler, Payload
from app.schemas.common import Notification


class ConfluenceHandler(BaseHandler):
    """Normalize supported Confluence content events."""

    service = ServiceType.CONFLUENCE

    def parse(self, payload: Payload) -> Notification:
        """Parse page, comment, and attachment payloads."""
        if self.event_type in {"page_created", "page_updated"}:
            return self._parse_page(payload)
        if self.event_type == "comment_created":
            return self._parse_comment(payload)
        if self.event_type == "attachment_created":
            return self._parse_attachment(payload)
        raise PayloadValidationError(
            f"Unsupported Confluence Handler event: {self.event_type}."
        )

    def _parse_page(self, payload: Payload) -> Notification:
        page = self.require_mapping(payload, "page")
        action = "생성" if self.event_type == "page_created" else "수정"
        page_title = str(page.get("title", "알 수 없음"))
        return self.build_notification(
            title=f"문서 {action}",
            description=str(page.get("title", "Confluence 문서가 변경되었습니다.")),
            fields=[
                ("스페이스", self._space_name(payload)),
                ("제목", page_title),
                ("작성자", self.user_name(payload.get("user"))),
                (
                    "발생 시각",
                    page.get("createdDate")
                    or page.get("lastModifiedDate")
                    or payload.get("timestamp", "알 수 없음"),
                ),
                (
                    "버전",
                    self.get_path(page, "version", "number", default="알 수 없음"),
                ),
            ],
            url=self._content_url(page),
            action_label="문서 열기",
            external_resource_id=str(page.get("id", page_title)),
            review_action="OPEN",
            review_thread_title=f"🧵 {page_title} 리뷰",
        )

    def _parse_comment(self, payload: Payload) -> Notification:
        comment = self.require_mapping(payload, "comment")
        page = payload.get("page", {})
        if not isinstance(page, Mapping):
            page = {}
        page_title = str(page.get("title", "알 수 없음"))
        return self.build_notification(
            title="댓글 추가",
            description=str(comment.get("body", comment.get("text", "")))[:300],
            fields=[
                ("스페이스", self._space_name(payload)),
                ("문서", page_title),
                ("작성자", self.user_name(payload.get("user"))),
            ],
            url=self._content_url(comment) or self._content_url(page),
            action_label="문서 열기",
            external_resource_id=str(page.get("id", page_title)),
            review_action="OPEN",
            review_thread_title=f"🧵 {page_title} 리뷰",
        )

    def _parse_attachment(self, payload: Payload) -> Notification:
        attachment = self.require_mapping(payload, "attachment")
        page = payload.get("page", {})
        if not isinstance(page, Mapping):
            page = {}
        page_title = str(page.get("title", "알 수 없음"))
        return self.build_notification(
            title="첨부파일 추가",
            description=str(attachment.get("title", "첨부파일이 추가되었습니다.")),
            fields=[
                ("스페이스", self._space_name(payload)),
                ("문서", page_title),
                ("파일명", attachment.get("title", "알 수 없음")),
                ("파일 크기", attachment.get("fileSize")),
                ("업로더", self.user_name(payload.get("user"))),
            ],
            url=self._content_url(attachment) or self._content_url(page),
            action_label="문서 열기",
            external_resource_id=str(page.get("id", page_title)),
            review_action="OPEN",
            review_thread_title=f"🧵 {page_title} 첨부파일 검토",
        )

    def _space_name(self, payload: Payload) -> str:
        space = payload.get("space", {})
        if isinstance(space, Mapping):
            return str(space.get("name") or space.get("key", "알 수 없음"))
        return "알 수 없음"

    @staticmethod
    def _content_url(content: Mapping[str, object]) -> str | None:
        for field in ("url", "webui", "self"):
            value = content.get(field)
            if isinstance(value, str) and value:
                return value
        links = content.get("_links")
        if isinstance(links, Mapping):
            value = links.get("webui")
            if isinstance(value, str) and value:
                if value.startswith(("https://", "http://")):
                    return value
                base = links.get("base")
                if isinstance(base, str) and base.startswith(("https://", "http://")):
                    return f"{base.rstrip('/')}/{value.lstrip('/')}"
        return None
