"""Provider-neutral Discord thread lifecycle contract."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import discord

from app.models.review_thread import ReviewThread
from app.schemas.common import Notification


@runtime_checkable
class ThreadManager(Protocol):
    """Manage one persistent Discord thread per external collaboration object."""

    async def create_thread(
        self,
        notification: Notification,
        project_id: int,
        message: discord.Message | None,
        channel_id: int | None = None,
    ) -> ReviewThread | None:
        """Create and persist a thread unless the provider object already has one."""
        ...

    def find_thread(self, provider: str, external_id: str) -> ReviewThread | None:
        """Find the persisted thread mapping for one provider object."""
        ...

    async def post_to_thread(
        self, provider: str, external_id: str, content: str
    ) -> bool:
        """Post content to an existing mapped thread."""
        ...

    async def archive_thread(
        self,
        provider: str,
        external_id: str,
        *,
        message: str | None = "✅ 작업이 완료되었습니다.",
        reason: str = "CollabNotify 작업 완료",
    ) -> bool:
        """Archive an existing mapped thread and persist completion."""
        ...

    async def process_notification(
        self,
        notification: Notification,
        project_id: int,
        message: discord.Message | None,
        channel_id: int | None = None,
        parent_embed: discord.Embed | None = None,
        parent_view: discord.ui.View | None = None,
    ) -> ReviewThread | None:
        """Apply normalized provider lifecycle metadata."""
        ...
