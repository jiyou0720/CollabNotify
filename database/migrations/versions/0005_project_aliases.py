"""Add external provider project aliases.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create aliases and preserve resolvable legacy name-based mappings."""
    op.create_table(
        "project_aliases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("external_name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "external_name", name="uq_project_alias_provider_name"
        ),
    )
    op.create_index(
        "ix_project_aliases_project_id",
        "project_aliases",
        ["project_id"],
    )

    # Existing managed projects previously routed by matching their internal name.
    # A provider channel proves that such a route was configured and can be migrated.
    op.execute(sa.text("""
            INSERT INTO project_aliases
                (project_id, provider, external_name, created_at, updated_at)
            SELECT MIN(p.id), cm.service,
                   CASE WHEN cm.service = 'github' THEN LOWER(p.name) ELSE p.name END,
                   CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM projects AS p
            JOIN channel_mappings AS cm ON cm.project_id = p.id
            WHERE p.service = 'discord'
              AND cm.service IN ('github', 'jira', 'confluence')
              AND NOT EXISTS (
                  SELECT 1 FROM project_aliases AS pa
                  WHERE pa.provider = cm.service
                    AND pa.external_name = CASE
                        WHEN cm.service = 'github' THEN LOWER(p.name) ELSE p.name END
              )
            GROUP BY cm.service, p.name
            HAVING COUNT(DISTINCT p.id) = 1
            """))

    # Older provider-specific rows can be linked when one managed project has the
    # same name. Ambiguous names are deliberately left for an administrator.
    op.execute(sa.text("""
            INSERT INTO project_aliases
                (project_id, provider, external_name, created_at, updated_at)
            SELECT MIN(managed.id), legacy.service,
                   CASE WHEN legacy.service = 'github'
                        THEN LOWER(legacy.name) ELSE legacy.name END,
                   CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM projects AS legacy
            JOIN projects AS managed
              ON managed.service = 'discord' AND managed.name = legacy.name
            WHERE legacy.service IN ('github', 'jira', 'confluence')
              AND NOT EXISTS (
                  SELECT 1 FROM project_aliases AS pa
                  WHERE pa.provider = legacy.service
                    AND pa.external_name = CASE
                        WHEN legacy.service = 'github'
                        THEN LOWER(legacy.name) ELSE legacy.name END
              )
            GROUP BY legacy.id, legacy.service, legacy.name
            HAVING COUNT(managed.id) = 1
            """))


def downgrade() -> None:
    """Remove external project aliases."""
    op.drop_index("ix_project_aliases_project_id", table_name="project_aliases")
    op.drop_table("project_aliases")
