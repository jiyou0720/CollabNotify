"""Tests for asynchronous retry behavior."""

from unittest.mock import AsyncMock

import pytest

from app.core.retry import RetryService


@pytest.mark.asyncio
async def test_retry_uses_documented_backoff() -> None:
    """Three transient failures must wait 1, 2, and 4 seconds."""
    operation = AsyncMock(
        side_effect=[TimeoutError(), TimeoutError(), TimeoutError(), "success"]
    )
    sleep = AsyncMock()
    retry = RetryService(sleep=sleep)

    result = await retry.run(operation, lambda exc: isinstance(exc, TimeoutError))

    assert result == "success"
    assert operation.await_count == 4
    assert [call.args[0] for call in sleep.await_args_list] == [1.0, 2.0, 4.0]


@pytest.mark.asyncio
async def test_retry_stops_after_final_failure() -> None:
    """The final transient failure must be re-raised after three retries."""
    operation = AsyncMock(side_effect=TimeoutError("timeout"))
    sleep = AsyncMock()

    with pytest.raises(TimeoutError, match="timeout"):
        await RetryService(sleep=sleep).run(operation, lambda _exc: True)

    assert operation.await_count == 4
    assert sleep.await_count == 3


@pytest.mark.asyncio
async def test_retry_does_not_retry_permanent_error() -> None:
    """Permanent errors must fail immediately without sleeping."""
    operation = AsyncMock(side_effect=PermissionError("forbidden"))
    sleep = AsyncMock()

    with pytest.raises(PermissionError, match="forbidden"):
        await RetryService(sleep=sleep).run(operation, lambda _exc: False)

    operation.assert_awaited_once_with()
    sleep.assert_not_awaited()
