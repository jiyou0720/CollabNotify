"""Add managed projects and automatic review threads.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Extend project mappings and create review lifecycle tables."""
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("discord_guild_id", sa.String()))
        batch.add_column(sa.Column("discord_category_id", sa.String()))
        batch.add_column(
            sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE")
        )
    with op.batch_alter_table("channel_mappings") as batch:
        batch.add_column(sa.Column("channel_name", sa.String()))

    op.create_table(
        "review_threads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("service", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("external_resource_id", sa.String(), nullable=False),
        sa.Column("discord_message_id", sa.String(), nullable=False),
        sa.Column("discord_thread_id", sa.String(), nullable=False, unique=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="IN_REVIEW"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "service", "external_resource_id", name="uq_review_service_resource"
        ),
    )
    op.create_index(
        "idx_review_thread_discord", "review_threads", ["discord_thread_id"]
    )
    op.create_index("idx_review_thread_status", "review_threads", ["status"])
    op.create_table(
        "reviewer_mappings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("discord_user_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "project_id", "discord_user_id", name="uq_reviewer_project_user"
        ),
    )
    op.create_table(
        "review_statuses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "review_thread_id",
            sa.Integer(),
            sa.ForeignKey("review_threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("changed_by_discord_id", sa.String()),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_review_status_thread", "review_statuses", ["review_thread_id"])


def downgrade() -> None:
    """Remove review lifecycle tables and managed-project columns."""
    op.drop_index("idx_review_status_thread", table_name="review_statuses")
    op.drop_table("review_statuses")
    op.drop_table("reviewer_mappings")
    op.drop_index("idx_review_thread_status", table_name="review_threads")
    op.drop_index("idx_review_thread_discord", table_name="review_threads")
    op.drop_table("review_threads")
    with op.batch_alter_table("channel_mappings") as batch:
        batch.drop_column("channel_name")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("status")
        batch.drop_column("discord_category_id")
        batch.drop_column("discord_guild_id")
