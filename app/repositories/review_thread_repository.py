"""Review thread persistence operations."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.change_request import ChangeRequest
from app.models.review_completion import ReviewCompletion
from app.models.review_status import ReviewStatus
from app.models.review_thread import ReviewThread


class ReviewThreadRepository:
    """Encapsulate review thread and status-history database access."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        project_id: int,
        service: str,
        event_type: str,
        external_resource_id: str,
        discord_message_id: str,
        discord_thread_id: str,
        title: str,
    ) -> ReviewThread:
        """Create and flush a review thread record."""
        review = ReviewThread(
            project_id=project_id,
            service=service,
            event_type=event_type,
            external_resource_id=external_resource_id,
            discord_message_id=discord_message_id,
            discord_thread_id=discord_thread_id,
            title=title,
        )
        self._session.add(review)
        self._session.flush()
        self.add_status(review.id, "IN_REVIEW")
        return review

    def find_by_resource(
        self, service: str, external_resource_id: str
    ) -> ReviewThread | None:
        """Find an active or archived review by external resource."""
        return self._session.scalar(
            select(ReviewThread).where(
                ReviewThread.service == service,
                ReviewThread.external_resource_id == external_resource_id,
            )
        )

    def find_by_discord_thread(self, thread_id: int) -> ReviewThread | None:
        """Find a review by Discord thread ID."""
        return self._session.scalar(
            select(ReviewThread).where(ReviewThread.discord_thread_id == str(thread_id))
        )

    def find_by_id(self, review_id: int) -> ReviewThread | None:
        """Find a review session by its database identifier."""
        return self._session.get(ReviewThread, review_id)

    def configure(self, review: ReviewThread, required_count: int) -> ReviewThread:
        """Set the manually selected approval threshold."""
        if required_count not in {1, 3}:
            raise ValueError("required_count must be 1 or 3")
        review.required_review_count = required_count
        self._session.flush()
        return review

    def add_completion(
        self, review: ReviewThread, discord_user_id: int, display_name: str
    ) -> tuple[ReviewCompletion, bool]:
        """Record one user's review completion, idempotently."""
        existing = self._session.scalar(
            select(ReviewCompletion).where(
                ReviewCompletion.review_thread_id == review.id,
                ReviewCompletion.discord_user_id == str(discord_user_id),
            )
        )
        if existing is not None:
            return existing, False
        completion = ReviewCompletion(
            review_thread_id=review.id,
            discord_user_id=str(discord_user_id),
            display_name=display_name,
        )
        self._session.add(completion)
        self._session.flush()
        return completion, True

    def list_completions(self, review_id: int) -> list[ReviewCompletion]:
        """List completed reviewers in chronological order."""
        return list(
            self._session.scalars(
                select(ReviewCompletion)
                .where(ReviewCompletion.review_thread_id == review_id)
                .order_by(ReviewCompletion.completed_at)
            )
        )

    def create_change_request(
        self,
        review: ReviewThread,
        requester_id: int,
        requester_name: str,
        title: str,
        body: str,
        location: str | None,
    ) -> ChangeRequest:
        """Create a structured open change request."""
        request = ChangeRequest(
            review_thread_id=review.id,
            requester_discord_id=str(requester_id),
            requester_name=requester_name,
            title=title,
            body=body,
            location=location,
            requested_page_version=review.last_page_version,
        )
        self._session.add(request)
        self._session.flush()
        return request

    def list_change_requests(
        self, review_id: int, statuses: tuple[str, ...] | None = None
    ) -> list[ChangeRequest]:
        """List structured requests, optionally filtered by status."""
        statement = select(ChangeRequest).where(
            ChangeRequest.review_thread_id == review_id
        )
        if statuses:
            statement = statement.where(ChangeRequest.status.in_(statuses))
        return list(self._session.scalars(statement.order_by(ChangeRequest.created_at)))

    def find_change_request(self, request_id: int) -> ChangeRequest | None:
        """Find a structured request by identifier."""
        return self._session.get(ChangeRequest, request_id)

    def resolve_change_request(self, request: ChangeRequest) -> None:
        """Mark a request resolved after its requester confirms the change."""
        request.status = "RESOLVED"
        request.resolved_at = datetime.now(UTC)
        self._session.flush()

    def cancel_change_request(self, request: ChangeRequest) -> None:
        """Cancel a request while preserving its audit history."""
        request.status = "CANCELLED"
        request.cancelled_at = datetime.now(UTC)
        self._session.flush()

    def list_open(self, project_id: int | None = None) -> list[ReviewThread]:
        """List reviews that are not completed."""
        statement = select(ReviewThread).where(ReviewThread.status != "COMPLETED")
        if project_id is not None:
            statement = statement.where(ReviewThread.project_id == project_id)
        return list(self._session.scalars(statement.order_by(ReviewThread.created_at)))

    def update_status(
        self,
        review: ReviewThread,
        status: str,
        *,
        changed_by_discord_id: str | None = None,
        note: str | None = None,
    ) -> ReviewThread:
        """Update current status and append immutable status history."""
        review.status = status
        self.add_status(review.id, status, changed_by_discord_id, note)
        self._session.flush()
        return review

    def add_status(
        self,
        review_thread_id: int,
        status: str,
        changed_by_discord_id: str | None = None,
        note: str | None = None,
    ) -> ReviewStatus:
        """Append one status transition."""
        history = ReviewStatus(
            review_thread_id=review_thread_id,
            status=status,
            changed_by_discord_id=changed_by_discord_id,
            note=note,
        )
        self._session.add(history)
        self._session.flush()
        return history

    def delete_for_project(self, project_id: int) -> int:
        """Delete all review threads through ORM cascades for a project."""
        reviews = list(
            self._session.scalars(
                select(ReviewThread).where(ReviewThread.project_id == project_id)
            )
        )
        for review in reviews:
            self._session.delete(review)
        self._session.flush()
        return len(reviews)
