"""Automatic Discord review thread lifecycle."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta

import discord
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import ConfluenceConfig
from app.core.enums import ServiceType
from app.core.exceptions import ChannelNotFoundError, InvalidConfigurationError
from app.models.review_thread import ReviewThread
from app.repositories.review_thread_repository import ReviewThreadRepository
from app.repositories.reviewer_repository import ReviewerRepository
from app.repositories.setting_repository import SettingRepository
from app.schemas.common import Notification, NotificationActivity
from app.services.confluence_service import ConfluenceService
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

□ 승인 또는 수정 요청을 남겨주세요."""


class ReviewThreadService:
    """Create and close review threads based on normalized event metadata."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        discord_service: DiscordService,
        confluence_service: ConfluenceService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._discord_service = discord_service
        config = ConfluenceConfig.from_env()
        self._confluence = (
            confluence_service
            if confluence_service is not None
            else ConfluenceService(config)
            if config is not None
            else None
        )
        self._logger = logging.getLogger(__name__)

    async def process_notification(
        self,
        notification: Notification,
        project_id: int,
        message: discord.Message | None,
        channel_id: int | None = None,
        parent_embed: discord.Embed | None = None,
        parent_view: discord.ui.View | None = None,
    ) -> ReviewThread | None:
        """Apply an OPEN or CLOSE review action after notification delivery."""
        resource_id = notification.external_resource_id
        if not resource_id or notification.review_action == "NONE":
            return None
        if notification.review_action == "APPEND":
            if self.find_thread(notification.service.value, resource_id) is None:
                if self._should_create_missing_thread(notification):
                    return await self.create_thread(
                        notification,
                        project_id,
                        message,
                        channel_id,
                    )
                self._log_missing(notification.service.value, resource_id)
                return None
            if notification.parent_update and channel_id is not None:
                await self.update_parent_message(
                    notification.service.value,
                    resource_id,
                    channel_id,
                    parent_embed,
                    parent_view,
                )
            await self.append_activities(
                notification.service.value,
                resource_id,
                notification.activities,
            )
            return None
        if notification.review_action == "CLOSE":
            await self.close_by_resource(notification.service.value, resource_id)
            return None
        return await self.create_thread(
            notification,
            project_id,
            message,
            channel_id,
        )

    async def create_thread(
        self,
        notification: Notification,
        project_id: int,
        message: discord.Message | None,
        channel_id: int | None = None,
    ) -> ReviewThread | None:
        """Create and persist one review thread for a normalized provider object."""
        resource_id = notification.external_resource_id
        if not resource_id:
            return None
        if not self._auto_thread_enabled():
            return None
        if message is None and channel_id is None:
            self._logger.warning(
                "Review thread source message missing: service=%s resource=%s",
                notification.service.value,
                resource_id,
            )
            return None

        existing = self.find_thread(notification.service.value, resource_id)
        if existing is not None:
            return existing

        title = notification.review_thread_title or f"🧵 {notification.title} 리뷰"
        if message is not None:
            thread = await self._discord_service.create_thread(
                message,
                title,
                self._auto_archive_duration(),
            )
            source_message_id = str(message.id)
        else:
            if channel_id is None:
                raise InvalidConfigurationError(
                    "리뷰 스레드를 생성할 Discord 채널이 없습니다."
                )
            thread = await self._discord_service.create_channel_thread(
                channel_id,
                title,
                self._auto_archive_duration(),
            )
            source_message_id = str(thread.id)
        try:
            with session_scope(self._session_factory) as session:
                review = ReviewThreadRepository(session).create(
                    project_id=project_id,
                    service=notification.service.value,
                    event_type=notification.event_type,
                    external_resource_id=resource_id,
                    discord_message_id=source_message_id,
                    discord_thread_id=str(thread.id),
                    title=title[:100],
                )
            if (
                notification.service is ServiceType.CONFLUENCE
                and notification.event_type == "page_created"
            ):
                await self._send_document_controls(review.id, thread)
            else:
                await self._discord_service.send_thread_message(
                    thread, REVIEW_CHECKLIST
                )
            for activity in notification.activities:
                await self._append_activity(int(thread.id), activity)
            self._logger.info(
                "Review thread created: service=%s resource=%s thread_id=%s",
                notification.service.value,
                resource_id,
                thread.id,
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

    async def append_activities(
        self,
        service: str,
        resource_id: str,
        activities: tuple[NotificationActivity, ...],
    ) -> bool:
        """Append normalized activities to an existing mapped review thread."""
        review = self.find_thread(service, resource_id)
        if review is None:
            self._log_missing(service, resource_id)
            return False
        thread_id = int(review.discord_thread_id)
        self._logger.info(
            "Review thread found: service=%s resource=%s thread_id=%s",
            service,
            resource_id,
            thread_id,
        )
        status_changes = [
            activity for activity in activities if activity.kind == "status"
        ]
        final_status = status_changes[-1] if status_changes else None
        github_reopened = any(
            activity.kind == "github_pr_reopened" for activity in activities
        )
        if github_reopened:
            await self.reopen_thread(
                service,
                resource_id,
                message="♻️ PR가 다시 열렸습니다.",
                reason="CollabNotify GitHub PR 재개",
                require_completed=False,
            )
        if (
            final_status is not None
            and self._is_done(final_status.before)
            and not self._is_done(final_status.after)
        ):
            await self.reopen_thread(service, resource_id)
        if service == ServiceType.CONFLUENCE.value:
            for activity in activities:
                if activity.kind == "confluence_page_updated":
                    await self.handle_document_updated(
                        resource_id, activity.after, activity.actor
                    )
        for activity in activities:
            await self._append_activity(thread_id, activity)
        if final_status is not None and self._is_done(final_status.after):
            await self.archive_thread(
                service,
                resource_id,
                reason="CollabNotify Jira 작업 완료",
            )
        if any(
            activity.kind in {"github_pr_closed", "github_pr_merged"}
            for activity in activities
        ):
            await self.archive_thread(
                service,
                resource_id,
                message=None,
                reason="CollabNotify GitHub PR 완료",
            )
        if any(activity.kind == "confluence_page_deleted" for activity in activities):
            await self.archive_thread(
                service,
                resource_id,
                message=None,
                reason="CollabNotify Confluence 문서 삭제",
            )
        return True

    async def handle_document_updated(
        self, page_id: str, version: str | None, actor: str | None
    ) -> None:
        """Mark open requests updated and mention their requesters for confirmation."""
        try:
            version_number = int(version) if version else None
        except ValueError:
            version_number = None
        with session_scope(self._session_factory) as session:
            repository = ReviewThreadRepository(session)
            review = repository.find_by_resource(ServiceType.CONFLUENCE.value, page_id)
            if review is None:
                return
            if version_number is not None:
                if (
                    review.last_page_version is not None
                    and version_number <= review.last_page_version
                ):
                    return
                review.last_page_version = version_number
            requests = repository.list_change_requests(review.id, ("OPEN",))
            for request in requests:
                request.status = "UPDATED"
                request.detected_page_version = version_number
            review_id = review.id
            thread_id = int(review.discord_thread_id)
            requester_ids = list(
                dict.fromkeys(item.requester_discord_id for item in requests)
            )
        if requester_ids:
            thread = self._discord_service.get_thread(thread_id)
            mentions = " ".join(f"<@{user_id}>" for user_id in requester_ids)
            await self._discord_service.send_thread_controls(
                thread,
                f"🔔 {mentions}\n문서가 수정되었습니다"
                + (f" (버전 {version_number})" if version_number else "")
                + f". 변경 내용을 확인해주세요.\n수정자: {actor or '알 수 없음'}",
                self.document_review_view(review_id),
            )
            await self.refresh_document_review(review_id)

    async def send_due_reminders(self) -> int:
        """Mention unfinished reviewers and unresolved requesters once per interval."""
        now = datetime.now(UTC)
        review_hours = max(1, int(os.getenv("REVIEW_REMINDER_HOURS", "48")))
        change_hours = max(1, int(os.getenv("CHANGE_REQUEST_REMINDER_HOURS", "48")))
        notifications: list[tuple[int, str, int]] = []
        with session_scope(self._session_factory) as session:
            repository = ReviewThreadRepository(session)
            for review in repository.list_open():
                if review.service != ServiceType.CONFLUENCE.value:
                    continue
                reviewers = ReviewerRepository(session).list_for_project(
                    review.project_id
                )
                completed_ids = {
                    item.discord_user_id
                    for item in repository.list_completions(review.id)
                }
                unfinished = [
                    item.discord_user_id
                    for item in reviewers
                    if item.discord_user_id not in completed_ids
                ]
                if (
                    review.required_review_count
                    and unfinished
                    and now - self._aware(review.created_at)
                    >= timedelta(hours=review_hours)
                    and (
                        review.review_reminded_at is None
                        or now - self._aware(review.review_reminded_at)
                        >= timedelta(hours=review_hours)
                    )
                ):
                    mentions = " ".join(f"<@{user_id}>" for user_id in unfinished)
                    notifications.append(
                        (
                            int(review.discord_thread_id),
                            "⏰ 리뷰 리마인더\n"
                            f"{mentions}\n"
                            "아직 문서 리뷰가 완료되지 않았습니다.",
                            review.id,
                        )
                    )
                    review.review_reminded_at = now
                open_requests = repository.list_change_requests(
                    review.id, ("OPEN", "UPDATED")
                )
                overdue = [
                    item
                    for item in open_requests
                    if now - self._aware(item.created_at)
                    >= timedelta(hours=change_hours)
                ]
                if overdue and (
                    review.change_reminded_at is None
                    or now - self._aware(review.change_reminded_at)
                    >= timedelta(hours=change_hours)
                ):
                    mentions = " ".join(
                        f"<@{user_id}>"
                        for user_id in dict.fromkeys(
                            item.requester_discord_id for item in overdue
                        )
                    )
                    notifications.append(
                        (
                            int(review.discord_thread_id),
                            "⏰ 수정 요청 리마인더\n"
                            f"{mentions}\n"
                            "열린 수정 요청을 확인해주세요.",
                            review.id,
                        )
                    )
                    review.change_reminded_at = now
        for thread_id, content, review_id in notifications:
            thread = self._discord_service.get_thread(thread_id)
            await self._discord_service.send_thread_controls(
                thread, content, self.document_review_view(review_id)
            )
        return len(notifications)

    def restore_document_review_views(self, client: discord.Client) -> int:
        """Register persistent Views for active Confluence sessions after restart."""
        count = 0
        with session_scope(self._session_factory) as session:
            for review in ReviewThreadRepository(session).list_open():
                if review.service == ServiceType.CONFLUENCE.value:
                    client.add_view(self.document_review_view(review.id))
                    count += 1
        return count

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )

    async def configure_document_review(
        self, review_id: int, actor_id: int, required_count: int
    ) -> None:
        """Apply the human-selected one-person or three-person threshold."""
        with session_scope(self._session_factory) as session:
            repository = ReviewThreadRepository(session)
            review = repository.find_by_id(review_id)
            if review is None or review.service != ServiceType.CONFLUENCE.value:
                raise InvalidConfigurationError("등록된 Confluence 리뷰가 아닙니다.")
            self._require_reviewer(session, review, actor_id)
            reviewers = ReviewerRepository(session).list_for_project(review.project_id)
            if required_count == 3 and len(reviewers) < 3:
                raise InvalidConfigurationError(
                    "전체 팀 기준에는 활성 리뷰어가 최소 3명 필요합니다."
                )
            repository.configure(review, required_count)
        await self.refresh_document_review(review_id)

    async def complete_document_review(
        self, review_id: int, user_id: int, display_name: str
    ) -> bool:
        """Idempotently record a reviewer, mirror it, and evaluate approval."""
        with session_scope(self._session_factory) as session:
            repository = ReviewThreadRepository(session)
            review = self._require_document_review(repository, review_id)
            self._require_reviewer(session, review, user_id)
            if review.required_review_count is None:
                raise InvalidConfigurationError("먼저 문서 리뷰 기준을 설정해주세요.")
            completion, created = repository.add_completion(
                review, user_id, display_name
            )
            page_id = review.external_resource_id
            completed_at = completion.completed_at
        if created and self._confluence is not None:
            try:
                comment_id = await self._confluence.add_comment(
                    page_id,
                    "[CollabNotify 리뷰 완료]\n"
                    f"{display_name}님이 리뷰를 완료했습니다.\n"
                    f"완료 시각: {completed_at.astimezone(UTC).isoformat()}",
                )
                with session_scope(self._session_factory) as session:
                    completion = ReviewThreadRepository(session).list_completions(
                        review_id
                    )
                    for item in completion:
                        if item.discord_user_id == str(user_id):
                            item.confluence_comment_id = comment_id
                            break
            except Exception:
                self._logger.exception(
                    "Confluence review comment synchronization failed"
                )
        await self.refresh_document_review(review_id)
        await self._try_approve(review_id)
        return created

    async def create_change_request(
        self,
        review_id: int,
        requester_id: int,
        requester_name: str,
        title: str,
        body: str,
        location: str | None,
    ) -> None:
        """Persist and mirror one Discord modal submission."""
        with session_scope(self._session_factory) as session:
            repository = ReviewThreadRepository(session)
            review = self._require_document_review(repository, review_id)
            self._require_reviewer(session, review, requester_id)
            change = repository.create_change_request(
                review, requester_id, requester_name, title, body, location
            )
            repository.update_status(
                review, "CHANGES_REQUESTED", changed_by_discord_id=str(requester_id)
            )
            page_id = review.external_resource_id
            request_id = change.id
            thread_id = int(review.discord_thread_id)
        comment_id = None
        if self._confluence is not None:
            try:
                comment_id = await self._confluence.add_comment(
                    page_id,
                    f"[CollabNotify 수정 요청 CR-{request_id}]\n"
                    f"요청자: {requester_name}\n"
                    f"제목: {title}\n관련 위치: {location or '미지정'}\n\n{body}",
                )
            except Exception:
                self._logger.exception(
                    "Confluence change request synchronization failed"
                )
        thread = self._discord_service.get_thread(thread_id)
        message = await self._discord_service.send_thread_controls(
            thread,
            f"📝 **수정 요청 CR-{request_id}**\n요청자: <@{requester_id}>\n"
            f"제목: {title}\n위치: {location or '미지정'}\n\n{body}",
            self.document_review_view(review_id),
        )
        with session_scope(self._session_factory) as session:
            change = ReviewThreadRepository(session).find_change_request(request_id)
            if change is not None:
                change.confluence_comment_id = comment_id
                change.discord_message_id = str(message.id)
        await self.refresh_document_review(review_id)

    async def resolve_latest_change_request(self, review_id: int, user_id: int) -> None:
        """Resolve the latest updated request owned by the clicking user."""
        with session_scope(self._session_factory) as session:
            repository = ReviewThreadRepository(session)
            self._require_document_review(repository, review_id)
            requests = repository.list_change_requests(review_id, ("UPDATED", "OPEN"))
            owned = [
                item for item in requests if item.requester_discord_id == str(user_id)
            ]
            if not owned:
                raise InvalidConfigurationError("확인할 본인의 수정 요청이 없습니다.")
            repository.resolve_change_request(owned[-1])
        await self.refresh_document_review(review_id)
        await self._try_approve(review_id)

    async def cancel_latest_change_request(self, review_id: int, user_id: int) -> None:
        """Cancel the latest open request owned by the clicking user."""
        with session_scope(self._session_factory) as session:
            repository = ReviewThreadRepository(session)
            self._require_document_review(repository, review_id)
            requests = repository.list_change_requests(review_id, ("OPEN", "UPDATED"))
            owned = [
                item for item in requests if item.requester_discord_id == str(user_id)
            ]
            if not owned:
                raise InvalidConfigurationError("취소할 본인의 수정 요청이 없습니다.")
            repository.cancel_change_request(owned[-1])
        await self.refresh_document_review(review_id)
        await self._try_approve(review_id)

    async def refresh_document_review(self, review_id: int) -> None:
        """Render current persisted state into the primary Discord message."""
        with session_scope(self._session_factory) as session:
            repository = ReviewThreadRepository(session)
            review = self._require_document_review(repository, review_id)
            completions = repository.list_completions(review_id)
            open_requests = repository.list_change_requests(
                review_id, ("OPEN", "UPDATED")
            )
            reviewers = ReviewerRepository(session).list_for_project(review.project_id)
            content = self._document_status_text(
                review, reviewers, completions, len(open_requests)
            )
            thread_id = int(review.discord_thread_id)
            message_id = (
                int(review.checklist_message_id)
                if review.checklist_message_id
                else None
            )
        thread = self._discord_service.get_thread(thread_id)
        view = self.document_review_view(review_id)
        if message_id is None:
            message = await self._discord_service.send_thread_controls(
                thread, content, view
            )
            with session_scope(self._session_factory) as session:
                review = ReviewThreadRepository(session).find_by_id(review_id)
                if review is not None:
                    review.checklist_message_id = str(message.id)
        else:
            await self._discord_service.edit_thread_controls(
                thread, message_id, content, view
            )

    def document_review_view(self, review_id: int) -> discord.ui.View:
        """Construct a persistent View without creating an import cycle."""
        from app.bot.document_review_views import DocumentReviewView

        return DocumentReviewView(self, review_id)

    async def _send_document_controls(
        self, review_id: int, thread: discord.Thread
    ) -> None:
        message = await self._discord_service.send_thread_controls(
            thread,
            "📋 **문서 리뷰**\n상태: 기준 설정 필요\n\n"
            "담당자가 일반 문서(1명) 또는 전체 팀 문서(3명)를 선택해주세요.",
            self.document_review_view(review_id),
        )
        with session_scope(self._session_factory) as session:
            review = ReviewThreadRepository(session).find_by_id(review_id)
            if review is not None:
                review.checklist_message_id = str(message.id)

    async def _try_approve(self, review_id: int) -> bool:
        with session_scope(self._session_factory) as session:
            repository = ReviewThreadRepository(session)
            review = self._require_document_review(repository, review_id)
            completions = repository.list_completions(review_id)
            open_requests = repository.list_change_requests(
                review_id, ("OPEN", "UPDATED")
            )
            if (
                review.status == "APPROVED"
                or review.required_review_count is None
                or len(completions) < review.required_review_count
                or open_requests
            ):
                return False
            page_id = review.external_resource_id
            reviewer_names = [item.display_name for item in completions]
            thread_id = int(review.discord_thread_id)
        if self._confluence is None:
            self._logger.warning(
                "Approval ready but Confluence outbound credentials are missing"
            )
            return False
        await self._confluence.mark_approved(page_id, reviewer_names)
        await self._confluence.add_comment(
            page_id,
            "[CollabNotify Approved]\n승인 기준을 충족했습니다.\n리뷰어: "
            + ", ".join(reviewer_names),
        )
        with session_scope(self._session_factory) as session:
            repository = ReviewThreadRepository(session)
            review = self._require_document_review(repository, review_id)
            repository.update_status(review, "APPROVED")
        thread = self._discord_service.get_thread(thread_id)
        await self._discord_service.send_thread_message(
            thread,
            "🎉 **Approved 승격**\n리뷰어: " + ", ".join(reviewer_names),
        )
        await self.refresh_document_review(review_id)
        return True

    @staticmethod
    def _require_document_review(
        repository: ReviewThreadRepository, review_id: int
    ) -> ReviewThread:
        review = repository.find_by_id(review_id)
        if review is None or review.service != ServiceType.CONFLUENCE.value:
            raise InvalidConfigurationError("등록된 Confluence 리뷰가 아닙니다.")
        if review.status in {"COMPLETED", "CANCELLED"}:
            raise InvalidConfigurationError("종료된 문서 리뷰입니다.")
        return review

    @staticmethod
    def _require_reviewer(session: Session, review: ReviewThread, user_id: int) -> None:
        reviewers = ReviewerRepository(session).list_for_project(review.project_id)
        if str(user_id) not in {item.discord_user_id for item in reviewers}:
            raise InvalidConfigurationError(
                "이 프로젝트의 지정 리뷰어만 사용할 수 있습니다."
            )

    @staticmethod
    def _document_status_text(
        review: ReviewThread,
        reviewers: list[object],
        completions: list[object],
        open_request_count: int,
    ) -> str:
        completed = {str(item.discord_user_id): item for item in completions}
        required = (
            str(review.required_review_count)
            if review.required_review_count
            else "미설정"
        )
        lines = [
            "📋 **문서 리뷰**",
            f"상태: {REVIEW_STATUS_LABELS.get(review.status, review.status)}",
            f"승인 기준: {required}명",
            f"리뷰 현황: {len(completions)}/{required}명 완료",
            f"열린 수정 요청: {open_request_count}건",
            "",
        ]
        for reviewer in reviewers:
            done = completed.get(str(reviewer.discord_user_id))
            suffix = " ✅" if done else " ⬜"
            lines.append(f"- <@{reviewer.discord_user_id}>{suffix}")
        return "\n".join(lines)

    async def update_parent_message(
        self,
        service: str,
        resource_id: str,
        channel_id: int,
        embed: discord.Embed | None,
        view: discord.ui.View | None = None,
    ) -> bool:
        """Update the original object embed while preserving its activity thread."""
        if embed is None:
            return False
        review = self.find_thread(service, resource_id)
        if review is None:
            self._log_missing(service, resource_id)
            return False
        try:
            message_id = int(review.discord_message_id)
            await self._discord_service.edit_channel_message(
                channel_id, message_id, embed, view
            )
        except (ValueError, TypeError, ChannelNotFoundError, discord.HTTPException):
            self._logger.warning(
                "Parent message update skipped: service=%s resource=%s message_id=%s",
                service,
                resource_id,
                review.discord_message_id,
                exc_info=True,
            )
            return False
        self._logger.info(
            "Parent message updated: service=%s resource=%s message_id=%s",
            service,
            resource_id,
            review.discord_message_id,
        )
        return True

    async def append_status_change(
        self, thread_id: int, activity: NotificationActivity
    ) -> None:
        """Append one status transition."""
        await self._send_activity(
            thread_id, self._change_message("🔄 상태 변경", activity)
        )
        self._logger.info("Jira status changed: thread_id=%s", thread_id)

    async def append_assignee_change(
        self, thread_id: int, activity: NotificationActivity
    ) -> None:
        """Append one assignee transition."""
        await self._send_activity(
            thread_id, self._change_message("👤 담당자 변경", activity)
        )

    async def append_priority_change(
        self, thread_id: int, activity: NotificationActivity
    ) -> None:
        """Append one priority transition."""
        await self._send_activity(
            thread_id, self._change_message("⚠️ 우선순위 변경", activity)
        )

    async def append_summary_change(
        self, thread_id: int, activity: NotificationActivity
    ) -> None:
        """Append one issue summary transition."""
        await self._send_activity(
            thread_id,
            self._change_message("✏️ 제목 변경", activity, arrow="↓"),
        )

    async def append_comment(
        self, thread_id: int, activity: NotificationActivity
    ) -> None:
        """Append a created, updated, or deleted Jira comment."""
        title = {
            "comment_created": "💬 새 댓글",
            "comment_updated": "✏️ 댓글 수정",
            "comment_deleted": "🗑 댓글 삭제",
        }[activity.kind]
        parts = [title]
        if activity.actor:
            parts.extend(("", "작성자:", activity.actor))
        if activity.body and activity.kind != "comment_deleted":
            parts.extend(("", activity.body))
        await self._send_activity(thread_id, "\n".join(parts))
        self._logger.info(
            "Jira comment activity appended: thread_id=%s kind=%s",
            thread_id,
            activity.kind,
        )

    async def append_resolution(
        self, thread_id: int, activity: NotificationActivity
    ) -> None:
        """Append one resolution transition."""
        await self._send_activity(
            thread_id,
            self._change_message("✅ 완료", activity, arrow="↓"),
        )

    async def append_commit(
        self, thread_id: int, activity: NotificationActivity
    ) -> None:
        """Append a compact pull-request synchronize summary."""
        count = activity.added[0] if activity.added else "알 수 없음"
        parts = ["📦 새로운 코드가 Push되었습니다.", "", f"커밋 수: {count}"]
        if activity.after:
            parts.extend(("", f"최신 커밋: `{activity.after}`"))
        if activity.body:
            parts.extend(("", "커밋 목록", activity.body))
        if activity.actor:
            parts.extend(("", "작성자", activity.actor))
        await self._send_activity(thread_id, "\n".join(parts))
        self._logger.info(
            "GitHub commit received: thread_id=%s count=%s", thread_id, count
        )

    async def append_review(
        self, thread_id: int, activity: NotificationActivity
    ) -> None:
        """Append a submitted, edited, or dismissed pull-request review."""
        state = (activity.after or "").casefold()
        if state == "approved":
            title = "✅ 리뷰 승인"
        elif state == "changes_requested":
            title = "🔄 변경 요청"
        elif activity.kind == "github_review_dismissed":
            title = "🗑 리뷰 해제"
        else:
            title = "✏️ 리뷰 수정" if activity.kind.endswith("edited") else "💬 리뷰"
        parts = [title]
        if activity.actor:
            parts.extend(("", "작성자", activity.actor))
        if activity.body:
            parts.extend(("", activity.body))
        await self._send_activity(thread_id, "\n".join(parts))
        self._logger.info(
            "GitHub review received: thread_id=%s state=%s", thread_id, state
        )

    async def append_review_comment(
        self, thread_id: int, activity: NotificationActivity
    ) -> None:
        """Append a pull-request inline review comment activity."""
        action = activity.kind.rsplit("_", 1)[-1]
        title = {
            "created": "💬 리뷰 댓글",
            "edited": "✏️ 리뷰 댓글 수정",
            "deleted": "🗑 리뷰 댓글 삭제",
        }[action]
        await self._send_activity(
            thread_id, self._authored_message(title, activity, action != "deleted")
        )
        self._logger.info(
            "GitHub review comment received: thread_id=%s action=%s",
            thread_id,
            action,
        )

    async def append_github_comment(
        self, thread_id: int, activity: NotificationActivity
    ) -> None:
        """Append a general issue comment made on a pull request."""
        action = activity.kind.rsplit("_", 1)[-1]
        title = {
            "created": "📝 댓글",
            "edited": "✏️ 댓글 수정",
            "deleted": "🗑 댓글 삭제",
        }[action]
        await self._send_activity(
            thread_id, self._authored_message(title, activity, action != "deleted")
        )
        self._logger.info(
            "GitHub comment received: thread_id=%s action=%s", thread_id, action
        )

    async def append_label(
        self, thread_id: int, activity: NotificationActivity
    ) -> None:
        """Append a pull-request label change."""
        added = activity.kind == "github_label_labeled"
        title = "🏷 라벨 추가" if added else "🏷 라벨 제거"
        label = activity.after or "알 수 없음"
        await self._send_activity(thread_id, f"{title}\n\n{label}")

    async def append_assignee(
        self, thread_id: int, activity: NotificationActivity
    ) -> None:
        """Append a pull-request assignee change."""
        action = "지정" if activity.kind == "github_assignee_assigned" else "해제"
        await self._send_activity(
            thread_id,
            f"👤 담당자 변경\n\n{activity.after or '알 수 없음'} ({action})",
        )

    async def append_push(self, thread_id: int, activity: NotificationActivity) -> None:
        """Alias synchronize handling to the compact commit summary."""
        await self.append_commit(thread_id, activity)

    async def archive_thread(
        self,
        provider: str,
        external_id: str,
        *,
        message: str | None = "✅ 작업이 완료되었습니다.",
        reason: str = "CollabNotify 작업 완료",
    ) -> bool:
        """Optionally post completion, archive a thread, and persist status."""
        review = self.find_thread(provider, external_id)
        if review is None:
            self._log_missing(provider, external_id)
            return False
        if review.status == "COMPLETED":
            return False
        thread_id = int(review.discord_thread_id)
        if message:
            await self._send_activity(thread_id, message)
        await self._discord_service.set_thread_archived(
            thread_id,
            archived=True,
            reason=reason,
        )
        self._set_review_status(provider, external_id, "COMPLETED")
        self._logger.info(
            "Review thread archived: service=%s resource=%s thread_id=%s",
            provider,
            external_id,
            thread_id,
        )
        return True

    async def reopen_thread(
        self,
        service: str,
        resource_id: str,
        *,
        message: str = "♻️ 작업이 다시 진행됩니다.",
        reason: str = "CollabNotify Jira 작업 재개",
        require_completed: bool = True,
    ) -> bool:
        """Unarchive a completed thread and persist its reopened state."""
        review = self.find_thread(service, resource_id)
        if review is None:
            self._log_missing(service, resource_id)
            return False
        if require_completed and review.status != "COMPLETED":
            return False
        thread_id = int(review.discord_thread_id)
        await self._discord_service.set_thread_archived(
            thread_id,
            archived=False,
            reason=reason,
        )
        await self._send_activity(thread_id, message)
        if review.status == "COMPLETED":
            self._set_review_status(service, resource_id, "IN_REVIEW")
        self._logger.info(
            "Review thread reopened: service=%s resource=%s thread_id=%s",
            service,
            resource_id,
            thread_id,
        )
        return True

    async def _append_activity(
        self, thread_id: int, activity: NotificationActivity
    ) -> None:
        handlers = {
            "status": self.append_status_change,
            "assignee": self.append_assignee_change,
            "priority": self.append_priority_change,
            "summary": self.append_summary_change,
            "resolution": self.append_resolution,
            "comment_created": self.append_comment,
            "comment_updated": self.append_comment,
            "comment_deleted": self.append_comment,
            "github_push": self.append_push,
            "github_review_submitted": self.append_review,
            "github_review_edited": self.append_review,
            "github_review_dismissed": self.append_review,
            "github_review_comment_created": self.append_review_comment,
            "github_review_comment_edited": self.append_review_comment,
            "github_review_comment_deleted": self.append_review_comment,
            "github_issue_comment_created": self.append_github_comment,
            "github_issue_comment_edited": self.append_github_comment,
            "github_issue_comment_deleted": self.append_github_comment,
            "github_label_labeled": self.append_label,
            "github_label_unlabeled": self.append_label,
            "github_assignee_assigned": self.append_assignee,
            "github_assignee_unassigned": self.append_assignee,
        }
        handler = handlers.get(activity.kind)
        if handler is not None:
            await handler(thread_id, activity)
            return
        if activity.kind == "description":
            await self._send_activity(thread_id, "📝 설명이 수정되었습니다.")
        elif activity.kind == "labels":
            changes = [*(f"+ {label}" for label in activity.added)]
            changes.extend(f"- {label}" for label in activity.removed)
            await self._send_activity(thread_id, "🏷 라벨 변경\n\n" + "\n".join(changes))
        elif activity.kind == "issue_deleted":
            await self._send_activity(thread_id, "🗑 이슈가 삭제되었습니다.")
        elif activity.kind == "github_pr_opened":
            await self._send_activity(
                thread_id,
                self._authored_message("📋 PR 요약", activity, include_body=True),
            )
            self._logger.info("GitHub PR opened: thread_id=%s", thread_id)
        elif activity.kind == "github_pr_edited":
            await self._send_activity(
                thread_id,
                self._authored_message("✏️ PR 정보 수정", activity, True),
            )
        elif activity.kind == "github_pr_ready_for_review":
            await self._send_activity(thread_id, "🚀 리뷰 준비 완료")
        elif activity.kind == "github_pr_converted_to_draft":
            await self._send_activity(thread_id, "📝 Draft PR로 변경")
        elif activity.kind in {
            "github_review_requested",
            "github_review_request_removed",
        }:
            title = (
                "👀 리뷰 요청"
                if activity.kind == "github_review_requested"
                else "🚫 리뷰 요청 취소"
            )
            await self._send_activity(thread_id, self._change_message(title, activity))
        elif activity.kind in {"github_pr_locked", "github_pr_unlocked"}:
            title = (
                "🔒 PR 대화 잠금"
                if activity.kind == "github_pr_locked"
                else "🔓 PR 대화 잠금 해제"
            )
            await self._send_activity(thread_id, title)
        elif activity.kind in {"github_pr_closed", "github_pr_merged"}:
            title = (
                "✅ PR Merged"
                if activity.kind == "github_pr_merged"
                else "🔒 PR Closed"
            )
            await self._send_activity(thread_id, title)
        elif activity.kind == "confluence_page_updated":
            details = ["📝 문서 수정"]
            if activity.actor:
                details.extend(("", "수정자:", activity.actor))
            if activity.occurred_at:
                details.extend(("", "수정 시각:", activity.occurred_at))
            previous_title = activity.added[0] if activity.added else None
            if previous_title and activity.body and previous_title != activity.body:
                details.extend(
                    ("", "제목 변경:", f"{previous_title} → {activity.body}")
                )
            await self._send_activity(thread_id, "\n".join(details))
        elif activity.kind == "confluence_comment_created":
            await self._send_activity(
                thread_id,
                self._authored_message("💬 새 댓글", activity, True),
            )
        elif activity.kind == "confluence_attachment_created":
            details = f"📎 첨부파일 추가\n\n{activity.body or '알 수 없음'}"
            if activity.after:
                details += f"\n크기: {activity.after} bytes"
            if activity.actor:
                details += f"\n업로더: {activity.actor}"
            await self._send_activity(thread_id, details)
        elif activity.kind == "confluence_page_deleted":
            await self._send_activity(thread_id, "🗑 문서가 삭제되었습니다.")

    async def _send_activity(self, thread_id: int, content: str) -> None:
        thread = self._discord_service.get_thread(thread_id)
        await self._discord_service.send_thread_message(thread, content[:2000])

    async def post_to_thread(
        self, provider: str, external_id: str, content: str
    ) -> bool:
        """Post a message through the shared persisted thread mapping."""
        review = self.find_thread(provider, external_id)
        if review is None:
            self._log_missing(provider, external_id)
            return False
        await self._send_activity(int(review.discord_thread_id), content)
        self._logger.info(
            "Review thread message posted: service=%s resource=%s thread_id=%s",
            provider,
            external_id,
            review.discord_thread_id,
        )
        return True

    @staticmethod
    def _authored_message(
        title: str, activity: NotificationActivity, include_body: bool
    ) -> str:
        parts = [title]
        if activity.actor:
            parts.extend(("", activity.actor))
        if include_body and activity.body:
            parts.extend(("", activity.body))
        return "\n".join(parts)

    @staticmethod
    def _change_message(
        title: str, activity: NotificationActivity, *, arrow: str = "→"
    ) -> str:
        before = activity.before or "없음"
        after = activity.after or "없음"
        message = f"{title}\n\n{before}\n{arrow}\n{after}"
        if activity.actor:
            message += f"\n\n변경한 사람:\n{activity.actor}"
        return message

    def find_thread(self, provider: str, external_id: str) -> ReviewThread | None:
        """Find one provider object to Discord thread mapping."""
        with session_scope(self._session_factory) as session:
            return ReviewThreadRepository(session).find_by_resource(
                provider, external_id
            )

    def _set_review_status(self, service: str, resource_id: str, status: str) -> None:
        with session_scope(self._session_factory) as session:
            repository = ReviewThreadRepository(session)
            review = repository.find_by_resource(service, resource_id)
            if review is not None:
                repository.update_status(review, status)

    def _log_missing(self, service: str, resource_id: str) -> None:
        self._logger.warning(
            "Review thread missing: service=%s resource=%s", service, resource_id
        )

    @staticmethod
    def _is_done(status: str | None) -> bool:
        return (status or "").strip().casefold() in {
            "done",
            "closed",
            "완료",
        }

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

    @staticmethod
    def _should_create_missing_thread(notification: Notification) -> bool:
        """Return whether a missing append mapping should bootstrap a thread."""
        return (
            notification.service is ServiceType.CONFLUENCE
            and notification.event_type == "page_updated"
        )
