"""Channel mapping persistence operations."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.channel import ChannelMapping


class ChannelRepository:
    """Encapsulate Discord channel mapping access."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        service: str,
        project_id: int,
        discord_channel_id: str,
        channel_name: str | None = None,
    ) -> ChannelMapping:
        """Create and flush a channel mapping."""
        mapping = ChannelMapping(
            service=service,
            project_id=project_id,
            discord_channel_id=discord_channel_id,
            channel_name=channel_name,
        )
        self._session.add(mapping)
        self._session.flush()
        return mapping

    def find_channel(self, service: str, project_id: int) -> ChannelMapping | None:
        """Find the configured channel for a service project."""
        statement = select(ChannelMapping).where(
            ChannelMapping.service == service,
            ChannelMapping.project_id == project_id,
        )
        return self._session.scalar(statement)

    def list_for_project(self, project_id: int) -> list[ChannelMapping]:
        """List all configured channels for one managed project."""
        statement = (
            select(ChannelMapping)
            .where(ChannelMapping.project_id == project_id)
            .order_by(ChannelMapping.service)
        )
        return list(self._session.scalars(statement))

    def set_channel(
        self,
        service: str,
        project_id: int,
        discord_channel_id: str,
        channel_name: str | None = None,
    ) -> ChannelMapping:
        """Create or update one service channel mapping."""
        mapping = self.find_channel(service, project_id)
        if mapping is None:
            return self.create(
                service,
                project_id,
                discord_channel_id,
                channel_name,
            )
        mapping.discord_channel_id = discord_channel_id
        mapping.channel_name = channel_name
        self._session.flush()
        return mapping

    def delete_service(self, service: str, project_id: int) -> bool:
        """Delete one service mapping if it exists."""
        result = self._session.execute(
            delete(ChannelMapping).where(
                ChannelMapping.service == service,
                ChannelMapping.project_id == project_id,
            )
        )
        return bool(result.rowcount)

    def delete_for_project(self, project_id: int) -> int:
        """Delete every channel mapping for one project."""
        result = self._session.execute(
            delete(ChannelMapping).where(ChannelMapping.project_id == project_id)
        )
        return result.rowcount or 0

    def delete(self, mapping: ChannelMapping) -> None:
        """Delete a channel mapping."""
        self._session.delete(mapping)
        self._session.flush()
