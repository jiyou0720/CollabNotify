"""Tests for the notification service contract."""

import inspect

import pytest

from app.services.notification_service import NotificationService


def test_notification_service_is_abstract() -> None:
    """Phase 2 must expose a contract without a concrete sender."""
    assert inspect.isabstract(NotificationService)

    with pytest.raises(TypeError):
        NotificationService()
