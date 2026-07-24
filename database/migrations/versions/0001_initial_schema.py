"""Create the initial CollabNotify schema.

Revision ID: 0001
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all MVP tables and indexes."""
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("service", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_projects_service", "projects", ["service"])
    op.create_table(
        "channel_mappings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("service", sa.String(), nullable=False),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("discord_channel_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("service", "project_id", name="uq_channel_service_project"),
    )
    op.create_table(
        "user_mappings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("service", sa.String(), nullable=False),
        sa.Column("external_username", sa.String(), nullable=False),
        sa.Column("discord_user_id", sa.String(), nullable=False),
        sa.Column("discord_display_name", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "service", "external_username", name="uq_user_service_username"
        ),
    )
    op.create_table(
        "role_mappings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role_name", sa.String(), nullable=False),
        sa.Column("discord_role_id", sa.String(), nullable=False),
        sa.UniqueConstraint("project_id", "role_name", name="uq_role_project_name"),
    )
    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("service", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
        ),
        sa.Column("external_event_id", sa.String()),
        sa.Column("discord_message_id", sa.String()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "service", "external_event_id", name="uq_notification_external_event"
        ),
    )
    op.create_index("idx_notification_event", "notification_logs", ["event_type"])
    op.create_index("idx_notification_processed", "notification_logs", ["processed_at"])
    op.create_table(
        "error_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("error_code", sa.String(), nullable=False),
        sa.Column("service", sa.String()),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text()),
        sa.Column("stack_trace", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_error_created", "error_logs", ["created_at"])
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(), unique=True, nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Drop all MVP tables in reverse dependency order."""
    op.drop_table("settings")
    op.drop_index("idx_error_created", table_name="error_logs")
    op.drop_table("error_logs")
    op.drop_index("idx_notification_processed", table_name="notification_logs")
    op.drop_index("idx_notification_event", table_name="notification_logs")
    op.drop_table("notification_logs")
    op.drop_table("role_mappings")
    op.drop_table("user_mappings")
    op.drop_table("channel_mappings")
    op.drop_index("ix_projects_service", table_name="projects")
    op.drop_table("projects")
