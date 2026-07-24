"""Tests for Confluence notification normalization."""

import pytest

from app.core.enums import ServiceType
from app.handlers.confluence.handler import ConfluenceHandler


@pytest.mark.asyncio
async def test_confluence_page_updated_notification() -> None:
    """Updated pages must expose space, author, and version."""
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
    assert fields["버전"] == "5"


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
