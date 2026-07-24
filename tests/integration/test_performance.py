"""Lightweight performance and concurrent-dispatch regression tests."""

import asyncio
from time import perf_counter

import pytest

from app.api.dependencies import get_event_dispatcher
from app.core.enums import ServiceType
from app.services.webhook_service import WebhookService


def github_payload(index: int) -> dict[str, object]:
    """Create a valid GitHub issue payload."""
    return {
        "action": "opened",
        "repository": {"full_name": "org/repo"},
        "issue": {"number": index, "title": f"Issue {index}"},
    }


@pytest.mark.asyncio
async def test_one_hundred_webhooks_process_within_one_second() -> None:
    """CPU-only normalization of 100 webhooks must remain below one second."""
    get_event_dispatcher.cache_clear()
    service = WebhookService(get_event_dispatcher())
    started_at = perf_counter()

    for index in range(100):
        result = await service.process(
            ServiceType.GITHUB, "issues", github_payload(index)
        )
        assert result.supported is True

    assert perf_counter() - started_at < 1.0


@pytest.mark.asyncio
async def test_twenty_webhooks_dispatch_concurrently() -> None:
    """Twenty concurrent webhook dispatches must complete without errors."""
    get_event_dispatcher.cache_clear()
    service = WebhookService(get_event_dispatcher())

    results = await asyncio.gather(
        *(
            service.process(ServiceType.GITHUB, "issues", github_payload(index))
            for index in range(20)
        )
    )

    assert all(result.supported for result in results)
