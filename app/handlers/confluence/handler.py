"""Confluence webhook event normalization."""

from collections.abc import Mapping
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser

from app.core.enums import ServiceType
from app.core.exceptions import PayloadValidationError
from app.handlers.base_handler import BaseHandler, Payload
from app.schemas.common import Notification, NotificationActivity


class _TextExtractor(HTMLParser):
    """Convert Confluence storage-format HTML to readable Discord text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        """Collect visible text nodes."""
        value = data.strip()
        if value:
            self.parts.append(value)

    def text(self) -> str:
        """Return normalized visible text."""
        return "\n".join(self.parts)


class ConfluenceHandler(BaseHandler):
    """Normalize supported Confluence content events."""

    service = ServiceType.CONFLUENCE

    def parse(self, payload: Payload) -> Notification:
        """Parse page, comment, attachment, and deletion payloads."""
        if self.event_type in {"page_created", "page_updated"}:
            return self._parse_page(payload)
        if self.event_type == "comment_created":
            return self._parse_comment(payload)
        if self.event_type == "attachment_created":
            return self._parse_attachment(payload)
        if self.event_type == "page_deleted":
            return self._parse_deleted_page(payload)
        raise PayloadValidationError(
            f"Unsupported Confluence Handler event: {self.event_type}."
        )

    def _parse_page(self, payload: Payload) -> Notification:
        page = self._page(payload)
        action = "생성" if self.event_type == "page_created" else "수정"
        page_title = str(page.get("title", "알 수 없음"))
        is_update = self.event_type == "page_updated"
        actor = self._actor(payload, page, is_update=is_update)
        occurred_at = self._occurred_at(payload, page, is_update=is_update)
        current_version = self._version_number(payload, page)
        previous_version = self._previous_version(payload, page, current_version)
        previous_title = self._first_text(
            payload.get("previousTitle"),
            page.get("previousTitle"),
            self.get_path(payload, "previousVersion", "title"),
        )
        return self.build_notification(
            title=f"문서 {action}",
            description=str(page.get("title", "Confluence 문서가 변경되었습니다.")),
            fields=[
                ("스페이스", self._space_name(payload)),
                ("제목", page_title),
                ("작성자" if self.event_type == "page_created" else "수정자", actor),
                ("수정 시각" if is_update else "생성 시각", occurred_at),
            ],
            url=self._content_url(page),
            action_label="문서 열기",
            external_resource_id=str(page.get("id", page_title)),
            review_action="OPEN" if self.event_type == "page_created" else "APPEND",
            review_thread_title=f"🧵 {page_title} 리뷰",
            activities=(
                (
                    NotificationActivity(
                        kind="confluence_page_updated",
                        actor=actor,
                        occurred_at=occurred_at,
                        before=previous_version,
                        after=current_version,
                        body=page_title,
                        added=(previous_title,) if previous_title else (),
                    ),
                )
                if self.event_type == "page_updated"
                else ()
            ),
            parent_delivery=self.event_type == "page_created",
            parent_update=self.event_type == "page_updated",
        )

    def _parse_comment(self, payload: Payload) -> Notification:
        comment = self.require_mapping(payload, "comment")
        page = self._page(payload)
        page_title = str(page.get("title", "알 수 없음"))
        actor = self._actor(payload, comment)
        body = self._body_text(comment)
        return self.build_notification(
            title="댓글 추가",
            description=body[:300],
            fields=[
                ("스페이스", self._space_name(payload)),
                ("문서", page_title),
                ("작성자", actor),
            ],
            url=self._content_url(comment) or self._content_url(page),
            action_label="문서 열기",
            external_resource_id=str(page.get("id", page_title)),
            review_action="APPEND",
            review_thread_title=f"🧵 {page_title} 리뷰",
            activities=(
                NotificationActivity(
                    kind="confluence_comment_created",
                    actor=actor,
                    occurred_at=self._occurred_at(payload, comment, is_update=False),
                    body=body[:1800],
                ),
            ),
            parent_delivery=False,
        )

    def _parse_attachment(self, payload: Payload) -> Notification:
        attachment = self.require_mapping(payload, "attachment")
        page = self._page(payload)
        page_title = str(page.get("title", "알 수 없음"))
        actor = self._actor(payload, attachment)
        file_name = (
            self._first_text(
                attachment.get("title"),
                attachment.get("fileName"),
                attachment.get("name"),
            )
            or "알 수 없음"
        )
        return self.build_notification(
            title="첨부파일 추가",
            description=file_name,
            fields=[
                ("스페이스", self._space_name(payload)),
                ("문서", page_title),
                ("파일명", file_name),
                ("파일 크기", attachment.get("fileSize")),
                ("업로더", actor),
            ],
            url=self._content_url(attachment) or self._content_url(page),
            action_label="문서 열기",
            external_resource_id=str(page.get("id", page_title)),
            review_action="APPEND",
            review_thread_title=f"🧵 {page_title} 첨부파일 검토",
            activities=(
                NotificationActivity(
                    kind="confluence_attachment_created",
                    actor=actor,
                    occurred_at=self._occurred_at(payload, attachment, is_update=False),
                    body=file_name,
                    after=(
                        str(attachment.get("fileSize"))
                        if attachment.get("fileSize") is not None
                        else None
                    ),
                ),
            ),
            parent_delivery=False,
        )

    def _parse_deleted_page(self, payload: Payload) -> Notification:
        page = self._page(payload)
        page_title = str(page.get("title", "알 수 없음"))
        return self.build_notification(
            title="문서 삭제",
            description="문서가 삭제되었습니다.",
            fields=[
                ("스페이스", self._space_name(payload)),
                ("문서", page_title),
                ("삭제한 사용자", self._actor(payload, page)),
            ],
            external_resource_id=str(page.get("id", page_title)),
            review_action="APPEND",
            review_thread_title=f"🧵 {page_title} 리뷰",
            activities=(
                NotificationActivity(
                    kind="confluence_page_deleted",
                    actor=self._actor(payload, page),
                    occurred_at=self._occurred_at(payload, page, is_update=True),
                ),
            ),
            parent_delivery=False,
        )

    def _page(self, payload: Payload) -> Mapping[str, object]:
        """Return a page from native webhook or Automation payload shapes."""
        for key in ("page", "content"):
            value = payload.get(key)
            if isinstance(value, Mapping):
                return value
        for key in ("comment", "attachment"):
            content = payload.get(key)
            if not isinstance(content, Mapping):
                continue
            container = content.get("container")
            if isinstance(container, Mapping):
                return container
        raise PayloadValidationError("Missing or invalid object: page.")

    def _actor(
        self,
        payload: Payload,
        content: Mapping[str, object],
        *,
        is_update: bool = False,
    ) -> str:
        """Resolve the actor from native and Automation webhook locations."""
        content_users = (
            (content.get("editor"), content.get("author"))
            if is_update
            else (content.get("author"), content.get("editor"))
        )
        candidates = (
            payload.get("user"),
            payload.get("actor"),
            payload.get("initiator"),
            payload.get("editor") if is_update else payload.get("author"),
            payload.get("displayName"),
            *content_users,
            content.get("user"),
            self.get_path(content, "version", "by"),
            self.get_path(content, "history", "createdBy"),
            (
                content.get("lastModifierAccountId")
                if is_update
                else content.get("creatorAccountId")
            ),
            payload.get("userAccountId"),
        )
        for candidate in candidates:
            name = self.user_name(candidate)
            if name != "알 수 없음":
                return name
        return "알 수 없음"

    def _occurred_at(
        self,
        payload: Payload,
        content: Mapping[str, object],
        *,
        is_update: bool,
    ) -> str:
        """Resolve an ISO timestamp from native and Automation payloads."""
        content_dates = (
            (
                content.get("updatedAt"),
                content.get("dateLastUpdated"),
                content.get("lastModifiedDate"),
                content.get("modificationDate"),
            )
            if is_update
            else (
                content.get("createdAt"),
                content.get("dateFirstPublished"),
                content.get("createdDate"),
                content.get("creationDate"),
            )
        )
        payload_dates = (
            (payload.get("updatedAt"), payload.get("modifiedAt"))
            if is_update
            else (payload.get("createdAt"), payload.get("creationDate"))
        )
        value = self._first_value(
            *content_dates,
            self.get_path(content, "version", "when"),
            *payload_dates,
            payload.get("occurredAt"),
            payload.get("timestamp"),
        )
        return self._format_timestamp(value) if value is not None else "알 수 없음"

    def _version_number(self, payload: Payload, page: Mapping[str, object]) -> str:
        for value in (page.get("version"), payload.get("version")):
            if isinstance(value, Mapping):
                number = self._first_text(value.get("number"), value.get("value"))
            else:
                number = self._first_text(value)
            if number:
                return number
        return self._first_text(page.get("versionNumber")) or "알 수 없음"

    def _previous_version(
        self, payload: Payload, page: Mapping[str, object], current: str
    ) -> str | None:
        explicit = self._first_text(
            self.get_path(payload, "previousVersion", "number"),
            payload.get("previousVersion"),
            page.get("previousVersion"),
        )
        if explicit:
            return explicit
        try:
            number = int(current)
        except ValueError:
            return None
        return str(number - 1) if number > 1 else None

    @staticmethod
    def _first_text(*values: object) -> str | None:
        for value in values:
            if value is not None and not isinstance(value, Mapping):
                text = str(value).strip()
                if text:
                    return text
        return None

    @staticmethod
    def _first_value(*values: object) -> object | None:
        for value in values:
            if value is not None and not isinstance(value, Mapping):
                if not isinstance(value, str) or value.strip():
                    return value
        return None

    @staticmethod
    def _format_timestamp(value: object) -> str:
        """Render native epoch milliseconds or preserve an Automation date string."""
        if isinstance(value, (int, float)) or (
            isinstance(value, str) and value.strip().isdigit()
        ):
            try:
                number = float(value)
                if number > 10_000_000_000:
                    number /= 1000
                return datetime.fromtimestamp(number, tz=UTC).isoformat()
            except (OSError, OverflowError, ValueError):
                return str(value).strip()
        return str(value).strip()

    @staticmethod
    def _body_text(content: Mapping[str, object]) -> str:
        value: object = content.get("text") or content.get("body") or ""
        if isinstance(value, Mapping):
            storage = value.get("storage")
            if isinstance(storage, Mapping):
                value = storage.get("value", "")
            else:
                value = value.get("value", "")
        parser = _TextExtractor()
        parser.feed(unescape(str(value)))
        return parser.text() or str(value)

    def _space_name(self, payload: Payload) -> str:
        space = payload.get("space", {})
        if not isinstance(space, Mapping):
            space = {}
        if not space:
            try:
                nested_space = self._page(payload).get("space", {})
            except PayloadValidationError:
                nested_space = {}
            if isinstance(nested_space, Mapping):
                space = nested_space
        if isinstance(space, Mapping):
            name = space.get("name") or space.get("key")
            if name:
                return str(name)
        page = self._page(payload)
        return (
            self._first_text(
                page.get("spaceName"),
                page.get("spaceKey"),
                payload.get("spaceName"),
                payload.get("spaceKey"),
            )
            or "알 수 없음"
        )

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
