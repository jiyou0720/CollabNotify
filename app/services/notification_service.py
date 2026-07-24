"""Notification delivery contract and Discord implementation."""

from abc import ABC, abstractmethod

import discord

from app.core.exceptions import DiscordApiError
from app.core.retry import RetryService
from app.models.notification import NotificationLog
from app.repositories.notification_repository import NotificationRepository
from app.schemas.common import Notification
from app.services.discord_service import DiscordService
from app.services.embed_builder import EmbedBuilder
from app.services.logging_service import LoggingService


class NotificationService(ABC):
    """Define the notification delivery boundary."""

    @abstractmethod
    async def send(
        self,
        channel_id: int,
        notification: Notification,
        *,
        content: str | None = None,
    ) -> discord.Message:
        """Deliver a normalized notification to a Discord channel."""


class DiscordNotificationService(NotificationService):
    """Build and deliver Discord notifications with retry and audit status."""

    def __init__(
        self,
        discord_service: DiscordService,
        embed_builder: EmbedBuilder,
        retry_service: RetryService,
        notification_repository: NotificationRepository | None = None,
    ) -> None:
        """Initialize notification delivery dependencies."""
        self._discord_service = discord_service
        self._embed_builder = embed_builder
        self._retry_service = retry_service
        self._repository = notification_repository
        self._logger = LoggingService(__name__)

    async def send(
        self,
        channel_id: int,
        notification: Notification,
        *,
        project_id: int | None = None,
        external_event_id: str | None = None,
        content: str | None = None,
        audit_log: NotificationLog | None = None,
    ) -> discord.Message:
        """Render and send a Notification, recording its final status."""
        embed = self._embed_builder.build(notification)
        view = self._embed_builder.build_view(notification)
        log = audit_log or self._create_log(notification, project_id, external_event_id)

        async def _operation() -> discord.Message:
            return await self._discord_service.send_embed(
                channel_id, embed, view, content
            )

        try:
            message = await self._retry_service.run(
                _operation, self._is_transient_discord_error
            )
        except Exception as exc:
            if log is not None and self._repository is not None:
                self._repository.update_status(log, "FAILED")
            self._logger.error(
                "Discord notification failed: service=%s event=%s",
                notification.service.value,
                notification.event_type,
                exc_info=True,
            )
            raise DiscordApiError("Discord notification delivery failed.") from exc

        if log is not None and self._repository is not None:
            self._repository.update_status(log, "SUCCESS", str(message.id))
        self._logger.info(
            "Discord notification sent: service=%s event=%s channel_id=%s",
            notification.service.value,
            notification.event_type,
            channel_id,
        )
        return message

    def _create_log(
        self,
        notification: Notification,
        project_id: int | None,
        external_event_id: str | None,
    ) -> NotificationLog | None:
        """Create a RETRY-state audit log when a Repository is configured."""
        if self._repository is None:
            return None
        return self._repository.create(
            service=notification.service.value,
            event_type=notification.event_type,
            project_id=project_id,
            external_event_id=external_event_id,
            status="RETRY",
        )

    @staticmethod
    def _is_transient_discord_error(exception: Exception) -> bool:
        """Identify timeout, network, rate-limit, and server failures."""
        if isinstance(exception, PermissionError):
            return False
        if isinstance(exception, (TimeoutError, OSError)):
            return True
        if isinstance(exception, discord.HTTPException):
            return exception.status == 429 or exception.status >= 500
        return False
