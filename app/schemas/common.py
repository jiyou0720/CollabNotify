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


class NotificationActivity(BaseModel):
    """One normalized external activity for an existing review thread."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str
    before: str | None = None
    after: str | None = None
    actor: str | None = None
    occurred_at: str | None = None
    body: str | None = None
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()


class Notification(BaseModel):
    """Normalized collaboration event before Discord rendering."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    service: ServiceType
    event_type: str
    title: str
    description: str
    fields: tuple[NotificationField, ...]
    actions: tuple[NotificationAction, ...] = ()
    activities: tuple[NotificationActivity, ...] = ()
    external_resource_id: str | None = None
    review_action: str = "NONE"
    review_thread_title: str | None = None
    parent_delivery: bool = True
    parent_update: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
