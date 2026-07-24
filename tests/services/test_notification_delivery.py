"""Tests for notification rendering, retry, and audit status."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import discord
import pytest
from sqlalchemy.orm import Session

from app.core.enums import ServiceType
from app.core.exceptions import DiscordApiError
from app.core.retry import RetryService
from app.repositories.notification_repository import NotificationRepository
from app.schemas.common import Notification
from app.services.discord_service import DiscordService
from app.services.embed_builder import EmbedBuilder
from app.services.notification_service import DiscordNotificationService


def create_notification() -> Notification:
    """Create a minimal delivery test Notification."""
    return Notification(
        service=ServiceType.GITHUB,
        event_type="issues",
        title="Issue Opened",
        description="Issue created.",
        fields=(),
    )


@pytest.mark.asyncio
async def test_notification_delivery_retries_and_marks_success(
    db_session: Session,
) -> None:
    """Transient delivery failures must retry and end in SUCCESS."""
    message = Mock(spec=discord.Message)
    message.id = 500
    discord_service = Mock(spec=DiscordService)
    discord_service.send_embed = AsyncMock(side_effect=[TimeoutError(), message])
    sleep = AsyncMock()
    repository = NotificationRepository(db_session)
    service = DiscordNotificationService(
        discord_service,
        EmbedBuilder(),
        RetryService(delays=(1,), sleep=sleep),
        repository,
    )

    result = await service.send(
        100, create_notification(), external_event_id="delivery-1"
    )

    assert result is message
    sleep.assert_awaited_once_with(1)
    logs = repository.find_recent(datetime.now(UTC) - timedelta(minutes=1))
    assert len(logs) == 1
    assert logs[0].status == "SUCCESS"
    assert logs[0].discord_message_id == "500"


@pytest.mark.asyncio
async def test_notification_delivery_marks_permanent_failure(
    db_session: Session,
) -> None:
    """Permanent failures must not retry and must store FAILED."""
    discord_service = Mock(spec=DiscordService)
    discord_service.send_embed = AsyncMock(side_effect=PermissionError("forbidden"))
    sleep = AsyncMock()
    repository = NotificationRepository(db_session)
    service = DiscordNotificationService(
        discord_service,
        EmbedBuilder(),
        RetryService(sleep=sleep),
        repository,
    )

    with pytest.raises(DiscordApiError):
        await service.send(100, create_notification(), external_event_id="delivery-2")

    sleep.assert_not_awaited()
    assert repository.find_failed()[0].status == "FAILED"
