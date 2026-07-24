"""Service-independent notification domain schemas."""

from datetime import UTC, datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.core.enums import ServiceType


class NotificationField(BaseModel):
    """One named value displayed in a notification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    value: str
    inline: bool = False


class NotificationAction(BaseModel):
    """A link action associated with a notification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str
    url: AnyHttpUrl


class Notification(BaseModel):
    """Normalized collaboration event before Discord rendering."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    service: ServiceType
    event_type: str
    title: str
    description: str
    fields: tuple[NotificationField, ...]
    actions: tuple[NotificationAction, ...] = ()
    external_resource_id: str | None = None
    review_action: str = "NONE"
    review_thread_title: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
