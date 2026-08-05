"""Administrator-only project slash commands."""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from app.bot.checks import require_guild, server_manager_only
from app.bot.error_handling import respond_to_command_error
from app.bot.views import DeleteConfirmationView
from app.models.project import Project
from app.services.project_alias_service import ProjectAliasService
from app.services.project_management_service import ProjectManagementService

logger = logging.getLogger(__name__)


class ProjectAliasCommandGroup(
    app_commands.Group,
    name="alias",
    description="외부 서비스 프로젝트 별칭을 관리합니다.",
):
    """Expose Korean project alias management commands."""

    def __init__(self, service: ProjectAliasService) -> None:
        super().__init__()
        self._service = service

    @app_commands.command(name="add", description="외부 프로젝트 별칭을 등록합니다.")
    @app_commands.describe(
        provider="외부 서비스",
        external_name="외부 서비스에서 사용하는 프로젝트 식별자",
        project_name="연결할 Discord 내부 프로젝트명",
    )
    @app_commands.choices(
        provider=[
            app_commands.Choice(name="GitHub", value="github"),
            app_commands.Choice(name="Jira", value="jira"),
            app_commands.Choice(name="Confluence", value="confluence"),
        ]
    )
    @server_manager_only
    async def add(
        self,
        interaction: discord.Interaction,
        provider: app_commands.Choice[str],
        external_name: str,
        project_name: str,
    ) -> None:
        """Register one provider identifier for an internal project."""
        guild = require_guild(interaction)
        alias = self._service.create_alias(
            guild.id, provider.value, external_name, project_name
        )
        await interaction.response.send_message(
            (
                f"**{alias.provider} / {alias.external_name}** 별칭을 "
                f"**{alias.project_name}** 프로젝트에 연결했습니다."
            ),
            ephemeral=True,
        )

    @app_commands.command(name="remove", description="외부 프로젝트 별칭을 삭제합니다.")
    @app_commands.describe(
        provider="외부 서비스",
        external_name="삭제할 외부 프로젝트 식별자",
    )
    @app_commands.choices(
        provider=[
            app_commands.Choice(name="GitHub", value="github"),
            app_commands.Choice(name="Jira", value="jira"),
            app_commands.Choice(name="Confluence", value="confluence"),
        ]
    )
    @server_manager_only
    async def remove(
        self,
        interaction: discord.Interaction,
        provider: app_commands.Choice[str],
        external_name: str,
    ) -> None:
        """Remove one provider identifier alias."""
        guild = require_guild(interaction)
        removed = self._service.delete_alias(guild.id, provider.value, external_name)
        message = (
            "외부 프로젝트 별칭을 삭제했습니다."
            if removed
            else "삭제할 외부 프로젝트 별칭이 없습니다."
        )
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="list", description="외부 프로젝트 별칭을 표시합니다.")
    @server_manager_only
    async def list_aliases(self, interaction: discord.Interaction) -> None:
        """List every alias owned by the current Discord guild."""
        guild = require_guild(interaction)
        aliases = self._service.find_all(guild.id)
        embed = discord.Embed(
            title="외부 프로젝트 별칭",
            color=discord.Color.blue(),
            description=(
                "\n".join(
                    f"• **{item.provider} / {item.external_name}** → "
                    f"{item.project_name}"
                    for item in aliases
                )
                or "등록된 외부 프로젝트 별칭이 없습니다."
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ProjectCommandGroup(
    app_commands.Group,
    name="project",
    description="프로젝트 Discord 서버 공간을 관리합니다.",
):
    """Expose managed project operations as Korean slash commands."""

    def __init__(
        self,
        service: ProjectManagementService,
        alias_service: ProjectAliasService,
    ) -> None:
        super().__init__()
        self._service = service
        self.add_command(ProjectAliasCommandGroup(alias_service))

    @app_commands.command(name="create", description="새 프로젝트 공간을 생성합니다.")
    @app_commands.describe(project_name="생성할 프로젝트명")
    @server_manager_only
    async def create(self, interaction: discord.Interaction, project_name: str) -> None:
        """Create a project category and all default channels."""
        guild = require_guild(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        result = await self._service.create_project(guild, project_name)
        embed = self._success_embed(
            "프로젝트가 생성되었습니다.",
            f"**{result.project.name}** 프로젝트 공간을 만들었습니다.",
        )
        embed.add_field(
            name="생성된 채널",
            value="\n".join(channel.mention for channel in result.channels.values()),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="delete", description="프로젝트 공간을 삭제합니다.")
    @app_commands.describe(project_name="삭제할 프로젝트명")
    @server_manager_only
    async def delete(self, interaction: discord.Interaction, project_name: str) -> None:
        """Delete a project after an explicit administrator confirmation."""
        guild = require_guild(interaction)
        view = DeleteConfirmationView(interaction.user.id)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="프로젝트 삭제 확인",
                description=(
                    f"**{project_name}** 프로젝트의 카테고리, 채널, 연결 정보와 "
                    "리뷰 설정을 모두 삭제합니다. 계속하시겠습니까?"
                ),
                color=discord.Color.red(),
            ),
            view=view,
            ephemeral=True,
        )
        timed_out = await view.wait()
        if timed_out or not view.confirmed:
            await interaction.edit_original_response(
                content="프로젝트 삭제를 취소했습니다.", embed=None, view=None
            )
            return
        await self._service.delete_project(guild, project_name)
        await interaction.edit_original_response(
            content="프로젝트를 삭제했습니다.", embed=None, view=None
        )

    @app_commands.command(name="archive", description="프로젝트를 보관합니다.")
    @app_commands.describe(project_name="보관할 프로젝트명")
    @server_manager_only
    async def archive(
        self, interaction: discord.Interaction, project_name: str
    ) -> None:
        """Archive project channels and disable notifications."""
        guild = require_guild(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        project = await self._service.archive_project(guild, project_name)
        await interaction.followup.send(
            embed=self._success_embed(
                "프로젝트를 보관했습니다.",
                f"**{project.name}** 알림을 비활성화했습니다.",
            ),
            ephemeral=True,
        )

    @app_commands.command(name="restore", description="보관된 프로젝트를 복원합니다.")
    @app_commands.describe(project_name="복원할 프로젝트명")
    @server_manager_only
    async def restore(
        self, interaction: discord.Interaction, project_name: str
    ) -> None:
        """Restore an archived project and notification delivery."""
        guild = require_guild(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        project = await self._service.restore_project(guild, project_name)
        await interaction.followup.send(
            embed=self._success_embed(
                "프로젝트를 복원했습니다.",
                f"**{project.name}** 알림을 다시 활성화했습니다.",
            ),
            ephemeral=True,
        )

    @app_commands.command(name="list", description="등록된 프로젝트 목록을 표시합니다.")
    @server_manager_only
    async def list_projects(self, interaction: discord.Interaction) -> None:
        """List managed projects with creation date and status."""
        guild = require_guild(interaction)
        projects = self._service.list_projects(guild.id)
        if not projects:
            embed = discord.Embed(title="프로젝트 목록", color=discord.Color.blue())
            embed.description = "등록된 프로젝트가 없습니다."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embeds = [
            self._project_list_embed(guild.id, projects[offset : offset + 25])
            for offset in range(0, len(projects), 25)
        ]
        await interaction.response.send_message(embed=embeds[0], ephemeral=True)
        for embed in embeds[1:]:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="info", description="프로젝트 연결 정보를 표시합니다.")
    @app_commands.describe(project_name="확인할 프로젝트명")
    @server_manager_only
    async def info(self, interaction: discord.Interaction, project_name: str) -> None:
        """Display category, provider channels, and webhook state."""
        guild = require_guild(interaction)
        project, mappings = self._service.project_info(guild.id, project_name)
        channels = {mapping.service: mapping.discord_channel_id for mapping in mappings}
        embed = discord.Embed(
            title=f"{project.name} 프로젝트 정보",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="카테고리",
            value=f"<#{project.discord_category_id}>",
            inline=False,
        )
        for service, label in (
            ("github", "GitHub 채널"),
            ("jira", "Jira 채널"),
            ("confluence", "Confluence 채널"),
        ):
            channel_id = channels.get(service)
            embed.add_field(
                name=label,
                value=f"<#{channel_id}>" if channel_id else "연결되지 않음",
            )
        embed.add_field(
            name="웹훅 상태",
            value="활성화" if project.enabled else "비활성화",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Return safe Korean command errors and retain diagnostic logs."""
        await respond_to_command_error(
            interaction,
            error,
            logger,
            "프로젝트 명령을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        )

    @staticmethod
    def _success_embed(title: str, description: str) -> discord.Embed:
        return discord.Embed(
            title=title,
            description=description,
            color=discord.Color.green(),
        )

    def _project_list_embed(
        self, guild_id: int, projects: list[Project]
    ) -> discord.Embed:
        """Build one Discord-safe page of up to 25 project fields."""
        embed = discord.Embed(title="프로젝트 목록", color=discord.Color.blue())
        for project in projects:
            state = "운영 중" if project.status == "ACTIVE" else "보관됨"
            mappings = self._service.project_info(guild_id, project.name)[1]
            channels = " ".join(
                f"<#{mapping.discord_channel_id}>" for mapping in mappings
            )
            embed.add_field(
                name=project.name,
                value=(
                    f"생성일: {project.created_at:%Y-%m-%d}\n"
                    f"상태: {state}\n연결된 채널: {channels or '없음'}"
                ),
                inline=False,
            )
        return embed
