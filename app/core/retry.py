"""Reusable asynchronous retry policy."""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar

ResultT = TypeVar("ResultT")


class RetryService:
    """Retry transient asynchronous operations with exponential backoff."""

    def __init__(
        self,
        delays: Sequence[float] = (1.0, 2.0, 4.0),
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        """Configure retry delays and an injectable sleep function."""
        self._delays = tuple(delays)
        self._sleep = sleep
        self._logger = logging.getLogger(__name__)

    async def run(
        self,
        operation: Callable[[], Awaitable[ResultT]],
        should_retry: Callable[[Exception], bool],
    ) -> ResultT:
        """Run an operation and retry only matching transient exceptions."""
        for retry_number in range(len(self._delays) + 1):
            try:
                return await operation()
            except Exception as exc:
                if retry_number >= len(self._delays) or not should_retry(exc):
                    raise
                delay = self._delays[retry_number]
                self._logger.warning(
                    "Retry scheduled: retry=%s delay_seconds=%s error_type=%s",
                    retry_number + 1,
                    delay,
                    type(exc).__name__,
                )
                await self._sleep(delay)
        raise RuntimeError("Retry loop exited unexpectedly.")
