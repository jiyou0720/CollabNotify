"""Project, channel, user, and role mapping resolution."""

from app.core.exceptions import InvalidConfigurationError
from app.models.role_mapping import RoleMapping
from app.models.user_mapping import UserMapping
from app.repositories.channel_repository import ChannelRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


class MappingService:
    """Resolve database mappings without exposing Repository details."""

    def __init__(
        self,
        channels: ChannelRepository,
        users: UserRepository,
        roles: RoleRepository,
    ) -> None:
        """Initialize mapping Repository dependencies."""
        self._channels = channels
        self._users = users
        self._roles = roles

    def find_channel(self, service: str, project_id: int) -> int:
        """Resolve a configured Discord channel for an internal project ID."""
        mapping = self._channels.find_channel(service, project_id)
        if mapping is None:
            raise InvalidConfigurationError(
                f"No channel mapping for {service}/project:{project_id}."
            )
        try:
            return int(mapping.discord_channel_id)
        except ValueError as exc:
            raise InvalidConfigurationError(
                "Configured Discord channel ID is invalid."
            ) from exc

    def find_user(self, service: str, username: str) -> UserMapping | None:
        """Resolve an optional Discord user mapping."""
        return self._users.find_discord_user(service, username)

    def find_role(self, project_id: int, role_name: str) -> RoleMapping | None:
        """Resolve an optional Discord role mapping."""
        return self._roles.find_role(project_id, role_name)
