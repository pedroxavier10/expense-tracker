"""Add category_hints table (learned description -> category corrections)

Revision ID: 0006_add_category_hints
Revises: 0005_google_auth
Create Date: 2026-11-26 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_add_category_hints"
down_revision: str | None = "0005_google_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "category_hints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column(
            "description_key",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=False,
        ),
        sa.Column(
            "description",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=False,
        ),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "description_key", name="uq_category_hints_user_key"),
    )
    op.create_index("ix_category_hints_user_id", "category_hints", ["user_id"], unique=False)
    op.create_index(
        "ix_category_hints_category_id", "category_hints", ["category_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_category_hints_category_id", table_name="category_hints")
    op.drop_index("ix_category_hints_user_id", table_name="category_hints")
    op.drop_table("category_hints")
