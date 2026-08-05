"""Persistent Discord controls for Confluence document reviews."""

from __future__ import annotations

import discord


class ChangeRequestModal(discord.ui.Modal):
    """Collect a structured document change request."""

    title_input = discord.ui.TextInput(label="요청 제목", max_length=100)
    body_input = discord.ui.TextInput(
        label="수정 내용", style=discord.TextStyle.paragraph, max_length=1500
    )
    location_input = discord.ui.TextInput(
        label="관련 위치 (선택)", required=False, max_length=300
    )

    def __init__(self, service: object, review_id: int) -> None:
        super().__init__(title="문서 수정 요청")
        self._service = service
        self._review_id = review_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        create = self._service.create_change_request
        await create(
            self._review_id,
            interaction.user.id,
            interaction.user.display_name,
            str(self.title_input),
            str(self.body_input),
            str(self.location_input).strip() or None,
        )
        await interaction.followup.send("수정 요청을 등록했습니다.", ephemeral=True)


class DocumentReviewView(discord.ui.View):
    """One persistent control set bound to a review session."""

    def __init__(self, service: object, review_id: int) -> None:
        super().__init__(timeout=None)
        self._service = service
        self._review_id = review_id
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.custom_id = f"{child.custom_id}:{review_id}"

    @discord.ui.button(
        label="일반 문서 (1명)",
        style=discord.ButtonStyle.secondary,
        custom_id="review:criteria:1",
    )
    async def criteria_one(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ) -> None:
        await self._configure(interaction, 1)

    @discord.ui.button(
        label="전체 팀 (3명)",
        style=discord.ButtonStyle.secondary,
        custom_id="review:criteria:3",
    )
    async def criteria_three(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ) -> None:
        await self._configure(interaction, 3)

    @discord.ui.button(
        label="리뷰 완료",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="review:complete",
    )
    async def complete(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        complete = self._service.complete_document_review
        created = await complete(
            self._review_id, interaction.user.id, interaction.user.display_name
        )
        message = (
            "리뷰 완료를 기록했습니다."
            if created
            else "이미 리뷰 완료로 기록되어 있습니다."
        )
        await interaction.followup.send(message, ephemeral=True)

    @discord.ui.button(
        label="수정 요청",
        emoji="📝",
        style=discord.ButtonStyle.primary,
        custom_id="review:change",
    )
    async def request_change(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(
            ChangeRequestModal(self._service, self._review_id)
        )

    @discord.ui.button(
        label="수정 확인 완료",
        style=discord.ButtonStyle.success,
        custom_id="review:resolve",
    )
    async def resolve(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        resolve = self._service.resolve_latest_change_request
        await resolve(self._review_id, interaction.user.id)
        await interaction.followup.send(
            "수정 요청을 해결 완료로 처리했습니다.", ephemeral=True
        )

    @discord.ui.button(
        label="요청 취소", style=discord.ButtonStyle.danger, custom_id="review:cancel"
    )
    async def cancel(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        cancel = self._service.cancel_latest_change_request
        await cancel(self._review_id, interaction.user.id)
        await interaction.followup.send(
            "최근 수정 요청을 취소했습니다.", ephemeral=True
        )

    async def _configure(self, interaction: discord.Interaction, count: int) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        configure = self._service.configure_document_review
        await configure(self._review_id, interaction.user.id, count)
        await interaction.followup.send(
            f"승인 기준을 {count}명으로 설정했습니다.", ephemeral=True
        )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, _item: discord.ui.Item
    ) -> None:
        message = str(error) or "요청을 처리하지 못했습니다."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
