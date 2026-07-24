"""Service and event based Handler dispatching."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Protocol

from app.core.enums import ServiceType
from app.core.exceptions import UnsupportedEventError


class EventHandler(Protocol):
    """Structural contract implemented by all event Handlers."""

    async def handle(self, payload: Mapping[str, Any]) -> object:
        """Handle one validated webhook payload."""
        ...


class EventDispatcher:
    """Register and invoke Handlers by service and event type."""

    def __init__(self) -> None:
        """Initialize an empty Handler registry."""
        self._handlers: dict[tuple[ServiceType, str], EventHandler] = {}
        self._logger = logging.getLogger(__name__)

    def register(
        self,
        service: ServiceType | str,
        event_type: str,
        handler: EventHandler,
    ) -> None:
        """Register a Handler for one normalized service-event key."""
        normalized_service = self.detect_service(service)
        normalized_event = self._normalize_event(event_type)
        self._handlers[(normalized_service, normalized_event)] = handler

    async def dispatch(
        self,
        service: ServiceType | str,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> object:
        """Dispatch an event to its registered Handler."""
        normalized_service = self.detect_service(service)
        normalized_event = self._normalize_event(event_type)
        handler = self.get_handler(normalized_service, normalized_event)
        self._logger.info(
            "Dispatching webhook: service=%s event=%s",
            normalized_service.value,
            normalized_event,
        )
        return await handler.handle(payload)

    @staticmethod
    def detect_service(service: ServiceType | str) -> ServiceType:
        """Normalize and validate a supported service value."""
        if isinstance(service, ServiceType):
            return service
        try:
            return ServiceType(service.strip().lower())
        except ValueError as exc:
            raise UnsupportedEventError(f"Unsupported service: {service}.") from exc

    @classmethod
    def detect_event(
        cls,
        service: ServiceType | str,
        payload: Mapping[str, Any],
        event_header: str | None = None,
    ) -> str:
        """Extract an event identifier using service-specific conventions."""
        normalized_service = cls.detect_service(service)
        if normalized_service is ServiceType.GITHUB:
            if event_header is None:
                raise UnsupportedEventError("Missing GitHub event header.")
            return cls._normalize_event(event_header)

        field = (
            "webhookEvent" if normalized_service is ServiceType.JIRA else "eventType"
        )
        event_type = payload.get(field)
        if not isinstance(event_type, str):
            raise UnsupportedEventError(f"Missing event field: {field}.")
        return cls._normalize_event(event_type)

    def get_handler(self, service: ServiceType | str, event_type: str) -> EventHandler:
        """Return a registered Handler or raise a meaningful exception."""
        normalized_service = self.detect_service(service)
        normalized_event = self._normalize_event(event_type)
        try:
            return self._handlers[(normalized_service, normalized_event)]
        except KeyError as exc:
            self._logger.warning(
                "Unsupported webhook event: service=%s event=%s",
                normalized_service.value,
                normalized_event,
            )
            raise UnsupportedEventError(
                f"Unsupported event: {normalized_service.value}/{normalized_event}."
            ) from exc

    @staticmethod
    def _normalize_event(event_type: str) -> str:
        """Normalize and validate an event identifier."""
        normalized = event_type.strip().lower()
        if not normalized:
            raise UnsupportedEventError("Event type cannot be empty.")
        return normalized
