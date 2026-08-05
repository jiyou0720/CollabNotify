"""Base behavior and parsing helpers for webhook Handlers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from app.core.enums import ServiceType
from app.core.exceptions import PayloadValidationError
from app.schemas.common import (
    Notification,
    NotificationAction,
    NotificationActivity,
    NotificationField,
)

type Payload = Mapping[str, Any]


class BaseHandler(ABC):
    """Validate and normalize one service event into a Notification."""

    service: ServiceType

    def __init__(self, event_type: str) -> None:
        """Bind the Handler to one Dispatcher event key."""
        self.event_type = event_type
        self._logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    async def handle(self, payload: Payload) -> Notification:
        """Validate and parse a webhook payload."""
        self.validate(payload)
        notification = self.parse(payload)
        self._logger.info(
            "Handler created notification: service=%s event=%s",
            self.service.value,
            self.event_type,
        )
        return notification

    def validate(self, payload: Payload) -> None:
        """Require a non-empty mapping payload."""
        if not payload:
            raise PayloadValidationError("Webhook payload cannot be empty.")

    @abstractmethod
    def parse(self, payload: Payload) -> Notification:
        """Parse a validated payload into a Notification."""

    def build_notification(
        self,
        *,
        title: str,
        description: str,
        fields: list[tuple[str, object]],
        url: str | None = None,
        action_label: str | None = None,
        external_resource_id: str | None = None,
        review_action: str = "NONE",
        review_thread_title: str | None = None,
        activities: tuple[NotificationActivity, ...] = (),
        parent_delivery: bool = True,
        parent_update: bool = False,
    ) -> Notification:
        """Build a normalized immutable Notification."""
        actions: tuple[NotificationAction, ...] = ()
        if url and action_label:
            actions = (NotificationAction(label=action_label, url=url),)

        return Notification(
            service=self.service,
            event_type=self.event_type,
            title=title,
            description=description,
            fields=tuple(
                NotificationField(name=name, value=self.to_text(value))
                for name, value in fields
                if value is not None and self.to_text(value)
            ),
            actions=actions,
            external_resource_id=external_resource_id,
            review_action=review_action,
            review_thread_title=review_thread_title,
            activities=activities,
            parent_delivery=parent_delivery,
            parent_update=parent_update,
        )

    @staticmethod
    def require_mapping(payload: Payload, field: str) -> Mapping[str, Any]:
        """Return a required nested mapping."""
        value = payload.get(field)
        if not isinstance(value, Mapping):
            raise PayloadValidationError(f"Missing or invalid object: {field}.")
        return value

    @staticmethod
    def get_path(payload: Payload, *path: str, default: object = None) -> object:
        """Read an optional nested mapping value."""
        current: object = payload
        for key in path:
            if not isinstance(current, Mapping):
                return default
            current = current.get(key, default)
        return current

    @staticmethod
    def user_name(value: object) -> str:
        """Extract a displayable external username."""
        if isinstance(value, Mapping):
            for key in (
                "displayName",
                "fullName",
                "publicName",
                "name",
                "login",
                "username",
            ):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate:
                    return candidate
        if isinstance(value, str) and value:
            return value
        return "알 수 없음"

    @staticmethod
    def to_text(value: object) -> str:
        """Convert common webhook values to readable text."""
        if value is None:
            return ""
        if isinstance(value, bool):
            return "예" if value else "아니요"
        if isinstance(value, list):
            return ", ".join(BaseHandler.to_text(item) for item in value) or "없음"
        if isinstance(value, Mapping):
            return BaseHandler.user_name(value)
        return str(value)
