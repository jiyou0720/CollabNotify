"""Reviewer mapping persistence operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reviewer_mapping import ReviewerMapping


class ReviewerRepository:
    """Encapsulate project reviewer assignments."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self, project_id: int, discord_user_id: int, display_name: str | None = None
    ) -> ReviewerMapping:
        """Add or reactivate a reviewer assignment and flush it."""
        existing = self._session.scalar(
            select(ReviewerMapping).where(
                ReviewerMapping.project_id == project_id,
                ReviewerMapping.discord_user_id == str(discord_user_id),
            )
        )
        if existing is not None:
            existing.enabled = True
            existing.display_name = display_name
            self._session.flush()
            return existing
        mapping = ReviewerMapping(
            project_id=project_id,
            discord_user_id=str(discord_user_id),
            display_name=display_name,
        )
        self._session.add(mapping)
        self._session.flush()
        return mapping

    def list_for_project(self, project_id: int) -> list[ReviewerMapping]:
        """List enabled reviewers for one project."""
        statement = select(ReviewerMapping).where(
            ReviewerMapping.project_id == project_id,
            ReviewerMapping.enabled.is_(True),
        )
        return list(self._session.scalars(statement))

    def remove(self, project_id: int, discord_user_id: int) -> bool:
        """Remove a reviewer assignment if present."""
        mapping = self._session.scalar(
            select(ReviewerMapping).where(
                ReviewerMapping.project_id == project_id,
                ReviewerMapping.discord_user_id == str(discord_user_id),
            )
        )
        if mapping is None:
            return False
        self._session.delete(mapping)
        self._session.flush()
        return True
