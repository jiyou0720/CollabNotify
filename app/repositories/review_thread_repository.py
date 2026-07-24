"""Review thread persistence operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

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
