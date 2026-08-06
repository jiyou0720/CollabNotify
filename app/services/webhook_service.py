"""End-to-end webhook orchestration."""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.core.enums import ServiceType
from app.core.exceptions import (
    DiscordApiError,
    InvalidConfigurationError,
    UnsupportedEventError,
)
from app.core.retry import RetryService
from app.dispatcher.dispatcher import EventDispatcher
from app.models.notification import NotificationLog
from app.repositories.channel_repository import ChannelRepository
from app.repositories.error_repository import ErrorRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import Notification
from app.services.discord_service import DiscordService
from app.services.embed_builder import EmbedBuilder
from app.services.mapping_service import MappingService
from app.services.notification_service import DiscordNotificationService
from app.services.project_alias_service import ProjectAliasService
from app.services.review_thread_service import ReviewThreadService
from app.services.thread_manager import ThreadManager
from database.session import session_scope


@dataclass(frozen=True, slots=True)
class WebhookProcessResult:
    """Outcome of one webhook processing request."""

    supported: bool
    duplicate: bool = False


class NotificationCoordinator:
    """Resolve mappings and deliver Notifications in one transaction."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        discord_service: DiscordService,
        embed_builder: EmbedBuilder | None = None,
        retry_service: RetryService | None = None,
        project_alias_service: ProjectAliasService | None = None,
        thread_manager: ThreadManager | None = None,
    ) -> None:
        """Initialize runtime delivery dependencies."""
        self._session_factory = session_factory
        self._discord_service = discord_service
        self._embed_builder = embed_builder or EmbedBuilder()
        self._retry_service = retry_service or RetryService()
        self._project_aliases = project_alias_service or ProjectAliasService(
            session_factory
        )
        self._review_threads: ThreadManager = thread_manager or ReviewThreadService(
            session_factory, discord_service
        )
        self._logger = logging.getLogger(__name__)

    async def deliver(
        self, notification: Notification, external_event_id: str | None
    ) -> bool:
        """Deliver one Notification, returning False for a duplicate event."""
        external_name = self._external_project_identifier(notification)
        alias = self._project_aliases.find_by_provider(
            notification.service.value, external_name
        )
        if alias is None:
            self._logger.warning(
                "Project alias not configured; notification ignored: "
                "provider=%s external_name=%s",
                notification.service.value,
                external_name,
            )
            return True
        with session_scope(self._session_factory) as session:
            projects = ProjectRepository(session)
            channels = ChannelRepository(session)
            mapping_service = MappingService(
                channels,
                UserRepository(session),
                RoleRepository(session),
            )
            notifications = NotificationRepository(session)
            project = projects.find_by_id(alias.project_id)
            if project is None or project.service != "discord" or not project.enabled:
                self._logger.warning(
                    "Project alias target is unavailable; notification ignored: "
                    "provider=%s external_name=%s project_id=%s",
                    notification.service.value,
                    external_name,
                    alias.project_id,
                )
                return True
            channel_id = mapping_service.find_channel(
                notification.service.value, project.id
            )
            mention_content = self._mention_content(
                notification, project.id, mapping_service
            )
            audit_log = self._claim_delivery(
                notifications,
                notification,
                project.id,
                external_event_id,
            )
            if audit_log is None:
                return False
            session.commit()

            delivery = DiscordNotificationService(
                self._discord_service,
                self._embed_builder,
                self._retry_service,
                notifications,
            )
            try:
                message = None
                bootstrap_parent = self._should_bootstrap_parent(notification)
                if notification.parent_delivery or bootstrap_parent:
                    message = await delivery.send(
                        channel_id,
                        notification,
                        project_id=project.id,
                        external_event_id=external_event_id,
                        content=mention_content,
                        audit_log=audit_log,
                    )
                else:
                    notifications.update_status(audit_log, "SUCCESS")
                session.commit()
                try:
                    parent_embed = (
                        self._embed_builder.build(notification)
                        if notification.parent_update
                        else None
                    )
                    parent_view = (
                        self._embed_builder.build_view(notification)
                        if notification.parent_update
                        else None
                    )
                    await self._review_threads.process_notification(
                        notification,
                        project.id,
                        message,
                        channel_id,
                        parent_embed,
                        parent_view,
                    )
                except Exception as review_error:
                    ErrorRepository(session).save(
                        error_code="DC003",
                        service=notification.service.value,
                        message=str(review_error),
                        stack_trace="".join(traceback.format_exception(review_error)),
                    )
                    session.commit()
                    self._logger.exception("Automatic review thread processing failed.")
            except Exception as exc:
                notifications.update_status(audit_log, "FAILED")
                ErrorRepository(session).save(
                    error_code=self._discord_error_code(notification.service),
                    service=notification.service.value,
                    message=str(exc),
                    stack_trace="".join(traceback.format_exception(exc)),
                )
                session.commit()
                raise
        return True

    def _should_bootstrap_parent(self, notification: Notification) -> bool:
        """Create a parent card when the first observed page event is not creation."""
        resource_id = notification.external_resource_id
        if (
            notification.service is not ServiceType.CONFLUENCE
            or notification.event_type
            not in {"page_updated", "comment_created", "attachment_created"}
            or not resource_id
        ):
            return False
        return (
            self._review_threads.find_thread(notification.service.value, resource_id)
            is None
        )

    def _claim_delivery(
        self,
        repository: NotificationRepository,
        notification: Notification,
        project_id: int,
        external_event_id: str | None,
    ) -> NotificationLog | None:
        """Atomically reserve an event before making the Discord API call."""
        if external_event_id:
            existing = repository.find_by_external_event(
                notification.service.value, external_event_id
            )
            if existing is not None:
                if existing.status != "FAILED":
                    return None
                repository.update_status(existing, "RETRY")
                return existing
        claimed = repository.claim(
            service=notification.service.value,
            event_type=notification.event_type,
            project_id=project_id,
            external_event_id=external_event_id,
        )
        if claimed is None:
            self._logger.info(
                "Concurrent duplicate webhook ignored: service=%s event_id=%s",
                notification.service.value,
                external_event_id,
            )
        return claimed

    @staticmethod
    def _mention_content(
        notification: Notification,
        project_id: int,
        mappings: MappingService,
    ) -> str | None:
        """Resolve explicitly represented users and roles to safe mentions."""
        user_fields = {
            "Author",
            "Reporter",
            "Assignee",
            "Reviewer",
            "Uploader",
            "작성자",
            "보고자",
            "담당자",
            "리뷰어",
            "업로더",
        }
        mentions: list[str] = []
        for field in notification.fields:
            if field.value == "Unknown":
                continue
            if field.name in user_fields:
                mapping = mappings.find_user(notification.service.value, field.value)
                if mapping is not None:
                    mentions.append(
                        DiscordService.mention_user(int(mapping.discord_user_id))
                    )
            elif field.name in {"Role", "역할"}:
                mapping = mappings.find_role(project_id, field.value)
                if mapping is not None:
                    mentions.append(
                        DiscordService.mention_role(int(mapping.discord_role_id))
                    )
        unique_mentions = list(dict.fromkeys(mentions))
        return " ".join(unique_mentions) or None

    @staticmethod
    def _discord_error_code(service: ServiceType) -> str:
        """Return the documented service-specific Discord failure code."""
        return {
            ServiceType.GITHUB: "GH005",
            ServiceType.JIRA: "JR005",
            ServiceType.CONFLUENCE: "CF005",
        }[service]

    def record_error(
        self,
        service: ServiceType,
        exception: Exception,
        error_code: str = "SYS003",
    ) -> None:
        """Persist an orchestration failure in an independent transaction."""
        with session_scope(self._session_factory) as session:
            ErrorRepository(session).save(
                error_code=error_code,
                service=service.value,
                message=str(exception),
                stack_trace="".join(traceback.format_exception(exception)),
            )

    @staticmethod
    def _external_project_identifier(notification: Notification) -> str:
        """Extract the service project identifier from normalized fields."""
        for name in (
            "Repository",
            "Project",
            "Space",
            "저장소",
            "프로젝트",
            "스페이스",
        ):
            for field in notification.fields:
                if field.name == name and field.value:
                    return field.value
        raise InvalidConfigurationError(
            "Notification does not contain a project identifier."
        )


class WebhookService:
    """Dispatch webhooks and optionally coordinate Discord delivery."""

    def __init__(
        self,
        dispatcher: EventDispatcher,
        coordinator: NotificationCoordinator | None = None,
    ) -> None:
        """Initialize dispatch and optional runtime delivery."""
        self._dispatcher = dispatcher
        self._coordinator = coordinator

    async def process(
        self,
        service: ServiceType,
        event_type: str,
        payload: dict[str, Any],
        external_event_id: str | None = None,
    ) -> WebhookProcessResult:
        """Run an event through Handler normalization and delivery."""
        notification = await self.normalize(service, event_type, payload)
        if notification is None:
            return WebhookProcessResult(supported=False)
        delivered = await self.deliver(notification, external_event_id)
        return WebhookProcessResult(supported=True, duplicate=not delivered)

    async def normalize(
        self,
        service: ServiceType,
        event_type: str,
        payload: dict[str, Any],
    ) -> Notification | None:
        """Dispatch and normalize an event without external side effects."""
        try:
            result = await self._dispatcher.dispatch(service, event_type, payload)
        except UnsupportedEventError:
            return None

        if not isinstance(result, Notification):
            raise TypeError("Webhook Handler must return a Notification.")
        return result

    async def deliver(
        self, notification: Notification, external_event_id: str | None
    ) -> bool:
        """Deliver a normalized Notification when runtime delivery is enabled."""
        if self._coordinator is None:
            return True
        return await self._coordinator.deliver(notification, external_event_id)

    async def deliver_safely(
        self, notification: Notification, external_event_id: str | None
    ) -> None:
        """Run post-response delivery without leaking task exceptions."""
        try:
            await self.deliver(notification, external_event_id)
        except Exception as exc:
            if self._coordinator is not None and not isinstance(exc, DiscordApiError):
                self._coordinator.record_error(notification.service, exc)
            logging.getLogger(__name__).exception(
                "Background notification delivery failed: service=%s event=%s",
                notification.service.value,
                notification.event_type,
            )

    @property
    def delivery_enabled(self) -> bool:
        """Report whether a Discord delivery coordinator is configured."""
        return self._coordinator is not None
