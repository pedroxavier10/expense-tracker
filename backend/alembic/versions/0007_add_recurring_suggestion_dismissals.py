"""Add recurring_suggestion_dismissals table (declined recurring-expense suggestions)

Revision ID: 0007_recurring_dismissals
Revises: 0006_add_category_hints
Create Date: 2026-11-26 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_recurring_dismissals"
down_revision: str | None = "0006_add_category_hints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recurring_suggestion_dismissals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "pattern_key",
            sqlmodel.sql.sqltypes.AutoString(length=600),
            nullable=False,
        ),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "pattern_key", name="uq_recurring_dismissals_user_key"),
    )
    op.create_index(
        "ix_recurring_suggestion_dismissals_user_id",
        "recurring_suggestion_dismissals",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_recurring_suggestion_dismissals_user_id",
        table_name="recurring_suggestion_dismissals",
    )
    op.drop_table("recurring_suggestion_dismissals")
