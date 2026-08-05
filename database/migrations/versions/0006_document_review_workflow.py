"""Add Discord-driven Confluence review workflow state.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add review criteria, completions, change requests, and reminders."""
    with op.batch_alter_table("review_threads") as batch:
        batch.add_column(sa.Column("required_review_count", sa.Integer()))
        batch.add_column(sa.Column("checklist_message_id", sa.String()))
        batch.add_column(sa.Column("last_page_version", sa.Integer()))
        batch.add_column(sa.Column("review_reminded_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("change_reminded_at", sa.DateTime(timezone=True)))

    op.create_table(
        "review_completions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("review_thread_id", sa.Integer(), nullable=False),
        sa.Column("discord_user_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("confluence_comment_id", sa.String()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["review_thread_id"], ["review_threads.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "review_thread_id", "discord_user_id", name="uq_review_completion_user"
        ),
    )
    op.create_table(
        "change_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("review_thread_id", sa.Integer(), nullable=False),
        sa.Column("requester_discord_id", sa.String(), nullable=False),
        sa.Column("requester_name", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=300)),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("requested_page_version", sa.Integer()),
        sa.Column("detected_page_version", sa.Integer()),
        sa.Column("confluence_comment_id", sa.String()),
        sa.Column("discord_message_id", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["review_thread_id"], ["review_threads.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_change_request_thread_status",
        "change_requests",
        ["review_thread_id", "status"],
    )


def downgrade() -> None:
    """Remove document review workflow state."""
    op.drop_index("idx_change_request_thread_status", table_name="change_requests")
    op.drop_table("change_requests")
    op.drop_table("review_completions")
    with op.batch_alter_table("review_threads") as batch:
        batch.drop_column("change_reminded_at")
        batch.drop_column("review_reminded_at")
        batch.drop_column("last_page_version")
        batch.drop_column("checklist_message_id")
        batch.drop_column("required_review_count")
