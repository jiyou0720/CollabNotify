"""Add the documented user mapping lookup index.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the service and external username lookup index."""
    op.create_index(
        "idx_user_service", "user_mappings", ["service", "external_username"]
    )


def downgrade() -> None:
    """Remove the user mapping lookup index."""
    op.drop_index("idx_user_service", table_name="user_mappings")
