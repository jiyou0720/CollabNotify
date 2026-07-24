"""User mapping persistence operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_mapping import UserMapping


class UserRepository:
    """Encapsulate external-to-Discord user mappings."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save_mapping(
        self,
        service: str,
        external_username: str,
        discord_user_id: str,
        discord_display_name: str | None = None,
    ) -> UserMapping:
        """Create and flush a user mapping."""
        mapping = UserMapping(
            service=service,
            external_username=external_username,
            discord_user_id=discord_user_id,
            discord_display_name=discord_display_name,
        )
        self._session.add(mapping)
        self._session.flush()
        return mapping

    def find_discord_user(
        self, service: str, external_username: str
    ) -> UserMapping | None:
        """Find a Discord mapping for an external username."""
        statement = select(UserMapping).where(
            UserMapping.service == service,
            UserMapping.external_username == external_username,
        )
        return self._session.scalar(statement)

    def delete_mapping(self, mapping: UserMapping) -> None:
        """Delete a user mapping."""
        self._session.delete(mapping)
        self._session.flush()
