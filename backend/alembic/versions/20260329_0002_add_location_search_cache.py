"""add location search cache

Revision ID: 20260329_0002
Revises: 20260329_0001
Create Date: 2026-03-29 00:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260329_0002"
down_revision: str | None = "20260329_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "location_search_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("query", sa.String(length=255), nullable=False),
        sa.Column("results_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("query"),
    )
    op.create_index(
        op.f("ix_location_search_cache_query"),
        "location_search_cache",
        ["query"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_location_search_cache_query"), table_name="location_search_cache")
    op.drop_table("location_search_cache")

