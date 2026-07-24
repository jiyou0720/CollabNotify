"""Automatic Discord review thread lifecycle."""

from __future__ import annotations

import logging

import discord
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import InvalidConfigurationError
from app.models.review_thread import ReviewThread
from app.repositories.review_thread_repository import ReviewThreadRepository
from app.repositories.setting_repository import SettingRepository
from app.schemas.common import Notification
from app.services.discord_service import DiscordService
from database.session import session_scope

REVIEW_STATUS_LABELS = {
    "IN_REVIEW": "🟡 검토 중",
    "APPROVED": "🟢 승인",
    "CHANGES_REQUESTED": "🔄 수정 요청",
    "REJECTED": "🔴 반려",
    "COMPLETED": "⚫ 완료",
}

REVIEW_CHECKLIST = """📋 리뷰 체크리스트

□ 내용을 확인했습니다.

□ 피드백을 작성했습니다.

□ 승인 또는 수정 요청을 남겨주세요.

현재 상태: 🟡 검토 중"""


class ReviewThreadService:
    """Create and close review threads based on normalized event metadata."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        discord_service: DiscordService,
    ) -> None:
        self._session_factory = session_factory
        self._discord_service = discord_service
        self._logger = logging.getLogger(__name__)

    async def process_notification(
        self,
        notification: Notification,
        project_id: int,
        message: discord.Message,
    ) -> ReviewThread | None:
        """Apply an OPEN or CLOSE review action after notification delivery."""
        resource_id = notification.external_resource_id
        if not resource_id or notification.review_action == "NONE":
            return None
        if notification.review_action == "CLOSE":
            await self.close_by_resource(notification.service.value, resource_id)
            return None
        if not self._auto_thread_enabled():
            return None

        with session_scope(self._session_factory) as session:
            existing = ReviewThreadRepository(session).find_by_resource(
                notification.service.value, resource_id
            )
            if existing is not None:
                return existing

        title = notification.review_thread_title or f"🧵 {notification.title} 리뷰"
        thread = await self._discord_service.create_thread(
            message,
            title,
            self._auto_archive_duration(),
        )
        await self._discord_service.send_thread_message(thread, REVIEW_CHECKLIST)
        try:
            with session_scope(self._session_factory) as session:
                review = ReviewThreadRepository(session).create(
                    project_id=project_id,
                    service=notification.service.value,
                    event_type=notification.event_type,
                    external_resource_id=resource_id,
                    discord_message_id=str(message.id),
                    discord_thread_id=str(thread.id),
                    title=title[:100],
                )
                return review
        except IntegrityError:
            self._logger.info(
                "Duplicate review thread race resolved: service=%s resource=%s",
                notification.service.value,
                resource_id,
            )
            await thread.edit(
                archived=True,
                reason="CollabNotify 중복 리뷰 스레드 정리",
            )
            return None
        except Exception:
            await thread.edit(
                archived=True,
                reason="CollabNotify 리뷰 스레드 저장 실패",
            )
            raise

    async def close_by_resource(self, service: str, resource_id: str) -> bool:
        """Complete and archive an existing review thread."""
        with session_scope(self._session_factory) as session:
            repository = ReviewThreadRepository(session)
            review = repository.find_by_resource(service, resource_id)
            if review is None or review.status == "COMPLETED":
                return False
            thread_id = int(review.discord_thread_id)
        await self._discord_service.archive_thread(thread_id)
        with session_scope(self._session_factory) as session:
            repository = ReviewThreadRepository(session)
            review = repository.find_by_resource(service, resource_id)
            if review is None:
                return False
            repository.update_status(review, "COMPLETED")
        return True

    async def update_status(
        self,
        discord_thread_id: int,
        status: str,
        changed_by_discord_id: int,
        note: str | None = None,
    ) -> ReviewThread:
        """Update review status and announce it in the Discord thread."""
        if status not in REVIEW_STATUS_LABELS:
            raise ValueError("지원하지 않는 리뷰 상태입니다.")

        with session_scope(self._session_factory) as session:
            review = ReviewThreadRepository(session).find_by_discord_thread(
                discord_thread_id
            )
            if review is None:
                raise InvalidConfigurationError("등록된 리뷰 스레드가 아닙니다.")
            if review.status == status:
                return review
            if review.status == "COMPLETED":
                raise InvalidConfigurationError(
                    "완료된 리뷰의 상태는 변경할 수 없습니다."
                )

        if status == "COMPLETED":
            await self._discord_service.archive_thread(discord_thread_id)
        else:
            thread = self._discord_service.get_thread(discord_thread_id)
            await self._discord_service.send_thread_message(
                thread,
                f"리뷰 상태가 **{REVIEW_STATUS_LABELS[status]}**(으)로 변경되었습니다.",
            )

        with session_scope(self._session_factory) as session:
            repository = ReviewThreadRepository(session)
            review = repository.find_by_discord_thread(discord_thread_id)
            if review is None:
                raise InvalidConfigurationError("리뷰 스레드가 삭제되었습니다.")
            repository.update_status(
                review,
                status,
                changed_by_discord_id=str(changed_by_discord_id),
                note=note,
            )
        return review

    def get_status(self, discord_thread_id: int) -> ReviewThread:
        """Return the current review record for one Discord thread."""
        with session_scope(self._session_factory) as session:
            review = ReviewThreadRepository(session).find_by_discord_thread(
                discord_thread_id
            )
            if review is None:
                raise InvalidConfigurationError("등록된 리뷰 스레드가 아닙니다.")
            return review

    def _auto_thread_enabled(self) -> bool:
        with session_scope(self._session_factory) as session:
            setting = SettingRepository(session).get("auto_thread")
            return setting is None or setting.value.strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }

    def _auto_archive_duration(self) -> int:
        with session_scope(self._session_factory) as session:
            setting = SettingRepository(session).get("archive_days")
            try:
                days = int(setting.value) if setting is not None else 1
            except ValueError:
                days = 1
        return {1: 1440, 3: 4320, 7: 10080}.get(days, 1440)
