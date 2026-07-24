"""Remove the redundant review thread lookup index.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the index duplicated by the Discord thread unique constraint."""
    op.drop_index("idx_review_thread_discord", table_name="review_threads")


def downgrade() -> None:
    """Restore the former redundant lookup index."""
    op.create_index(
        "idx_review_thread_discord",
        "review_threads",
        ["discord_thread_id"],
    )
