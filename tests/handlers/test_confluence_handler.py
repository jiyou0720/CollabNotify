"""Tests for Confluence notification normalization."""

import pytest

from app.core.enums import ServiceType
from app.handlers.confluence.handler import ConfluenceHandler


@pytest.mark.asyncio
async def test_confluence_page_updated_notification() -> None:
    """Updated pages must expose space and author without version field."""
    payload = {
        "page": {
            "title": "Architecture",
            "version": {"number": 5},
            "url": "https://confluence.example/page",
        },
        "space": {"name": "Development"},
        "user": {"displayName": "Editor"},
    }

    notification = await ConfluenceHandler("page_updated").handle(payload)
    fields = {field.name: field.value for field in notification.fields}

    assert notification.service is ServiceType.CONFLUENCE
    assert notification.title == "문서 수정"
    assert fields["스페이스"] == "Development"
    assert "버전" not in fields
    assert notification.review_action == "APPEND"
    assert notification.parent_delivery is False
    assert notification.parent_update is True
    assert notification.activities[0].kind == "confluence_page_updated"
    assert notification.activities[0].before == "4"
    assert notification.activities[0].after == "5"


@pytest.mark.asyncio
async def test_confluence_automation_page_created_fields() -> None:
    """Automation payloads must populate every required creation Embed value."""
    notification = await ConfluenceHandler("page_created").handle(
        {
            "content": {
                "id": "42",
                "title": "운영 가이드",
                "version": {
                    "number": 1,
                    "when": "2026-07-26T10:20:30.000Z",
                    "by": {"displayName": "홍길동"},
                },
                "_links": {
                    "base": "https://example.atlassian.net/wiki",
                    "webui": "/spaces/DEV/pages/42",
                },
            },
            "space": {"name": "개발팀"},
        }
    )
    fields = {field.name: field.value for field in notification.fields}

    assert notification.external_resource_id == "42"
    assert fields == {
        "스페이스": "개발팀",
        "제목": "운영 가이드",
        "작성자": "홍길동",
        "생성 시각": "2026-07-26T10:20:30.000Z",
    }
    assert str(notification.actions[0].url).endswith("/spaces/DEV/pages/42")


@pytest.mark.asyncio
async def test_confluence_page_update_records_time_version_and_title() -> None:
    """Page updates must normalize complete timeline metadata."""
    notification = await ConfluenceHandler("page_updated").handle(
        {
            "page": {
                "id": "42",
                "title": "새 제목",
                "version": {"number": 8, "when": "2026-07-26T11:00:00Z"},
            },
            "previousVersion": {"number": 7, "title": "이전 제목"},
            "actor": {"displayName": "수정자"},
            "space": {"name": "개발팀"},
        }
    )
    activity = notification.activities[0]

    assert activity.actor == "수정자"
    assert activity.occurred_at == "2026-07-26T11:00:00Z"
    assert activity.before == "7"
    assert activity.after == "8"
    assert activity.added == ("이전 제목",)


@pytest.mark.asyncio
async def test_confluence_attachment_notification() -> None:
    """Attachments must expose their file name and uploader."""
    payload = {
        "attachment": {"title": "diagram.png", "fileSize": 2048},
        "page": {"title": "Architecture"},
        "user": {"displayName": "Uploader"},
    }

    notification = await ConfluenceHandler("attachment_created").handle(payload)
    fields = {field.name: field.value for field in notification.fields}

    assert fields["파일명"] == "diagram.png"
    assert fields["업로더"] == "Uploader"
    assert notification.review_action == "APPEND"
    assert notification.parent_delivery is False
    assert notification.activities[0].kind == "confluence_attachment_created"


@pytest.mark.asyncio
async def test_confluence_comment_appends_to_page_thread() -> None:
    """A page comment targets the existing page review thread."""
    notification = await ConfluenceHandler("comment_created").handle(
        {
            "comment": {"body": "검토 의견"},
            "page": {"id": "10", "title": "Architecture"},
            "space": {"name": "Development"},
            "user": {"displayName": "Reviewer"},
        }
    )

    assert notification.external_resource_id == "10"
    assert notification.review_action == "APPEND"
    assert notification.parent_delivery is False
    assert notification.activities[0].kind == "confluence_comment_created"


@pytest.mark.asyncio
async def test_confluence_storage_comment_is_plain_text() -> None:
    """Storage-format HTML must not leak tags into Discord."""
    notification = await ConfluenceHandler("comment_created").handle(
        {
            "comment": {
                "body": {"storage": {"value": "<p>검토 <b>완료</b></p>"}},
                "author": {"displayName": "검토자"},
            },
            "page": {"id": "10", "title": "Architecture"},
        }
    )

    activity = notification.activities[0]
    assert activity.actor == "검토자"
    assert activity.body == "검토\n완료"


@pytest.mark.asyncio
async def test_confluence_native_comment_uses_container_page() -> None:
    """Native comment payloads may identify their page through container."""
    notification = await ConfluenceHandler("comment_created").handle(
        {
            "comment": {
                "body": {"storage": {"value": "<p>좋습니다.</p>"}},
                "container": {
                    "id": "77",
                    "title": "설계",
                    "space": {"name": "개발팀"},
                },
            },
            "actor": {"displayName": "검토자"},
        }
    )
    fields = {field.name: field.value for field in notification.fields}

    assert notification.external_resource_id == "77"
    assert fields["스페이스"] == "개발팀"


@pytest.mark.asyncio
async def test_confluence_attachment_accepts_file_name() -> None:
    """Automation may expose the attachment filename as fileName."""
    notification = await ConfluenceHandler("attachment_created").handle(
        {
            "attachment": {
                "fileName": "runbook.pdf",
                "container": {"id": "77", "title": "설계"},
            },
            "user": {"displayName": "업로더"},
        }
    )

    assert notification.activities[0].body == "runbook.pdf"


@pytest.mark.asyncio
async def test_confluence_automation_flat_metadata_is_never_lost() -> None:
    """Official Automation values may be sent as flat scalar fields."""
    notification = await ConfluenceHandler("page_updated").handle(
        {
            "page": {
                "id": "88",
                "title": "운영 문서",
                "spaceKey": "OPS",
            },
            "editor": "박지유",
            "updatedAt": "2026-07-27T09:30:00Z",
            "version": "12",
            "previousVersion": "11",
        }
    )
    fields = {field.name: field.value for field in notification.fields}

    assert fields["스페이스"] == "OPS"
    assert fields["수정자"] == "박지유"
    assert fields["수정 시각"] == "2026-07-27T09:30:00Z"
    assert "버전" not in fields
    assert "알 수 없음" not in fields.values()


@pytest.mark.asyncio
async def test_confluence_official_page_smart_values_are_normalized() -> None:
    """Nested Confluence Automation page smart values populate metadata."""
    notification = await ConfluenceHandler("page_updated").handle(
        {
            "page": {
                "id": "99",
                "title": "배포 절차",
                "space": {"name": "운영팀"},
                "author": {"fullName": "최초 작성자"},
                "editor": {"fullName": "최근 수정자"},
                "dateFirstPublished": "2026-07-26T08:00:00.000Z",
                "dateLastUpdated": "2026-07-27T09:30:00.000Z",
                "version": {"number": 7},
            },
            "previousVersion": {"number": 6},
        }
    )
    fields = {field.name: field.value for field in notification.fields}

    assert fields["스페이스"] == "운영팀"
    assert fields["수정자"] == "최근 수정자"
    assert fields["수정 시각"] == "2026-07-27T09:30:00.000Z"
    assert "버전" not in fields
    assert notification.activities[0].before == "6"
    assert notification.activities[0].after == "7"
    assert "알 수 없음" not in fields.values()


@pytest.mark.asyncio
async def test_confluence_native_webhook_metadata_is_normalized() -> None:
    """Native scalar version and epoch dates must map to readable fields."""
    notification = await ConfluenceHandler("page_created").handle(
        {
            "userAccountId": "account-123",
            "page": {
                "id": 16777227,
                "title": "Native Page",
                "spaceKey": "DEV",
                "creatorAccountId": "account-123",
                "creationDate": 1594752539309,
                "version": 1,
                "self": "https://example.atlassian.net/wiki/pages/16777227",
            },
            "timestamp": 1594752539400,
        }
    )
    fields = {field.name: field.value for field in notification.fields}

    assert fields["작성자"] == "account-123"
    assert fields["생성 시각"].startswith("2020-07-14T")
    assert "버전" not in fields
    assert fields["스페이스"] == "DEV"


@pytest.mark.asyncio
async def test_confluence_page_deleted_targets_existing_thread() -> None:
    """Deletion must append to, then archive, the page's mapped thread."""
    notification = await ConfluenceHandler("page_deleted").handle(
        {
            "page": {"id": "10", "title": "Architecture"},
            "user": {"displayName": "관리자"},
            "timestamp": "2026-07-26T12:00:00Z",
        }
    )

    assert notification.external_resource_id == "10"
    assert notification.review_action == "APPEND"
    assert notification.parent_delivery is False
    assert notification.activities[0].kind == "confluence_page_deleted"
