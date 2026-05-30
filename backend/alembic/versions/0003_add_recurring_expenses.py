"""Add recurring expenses table and link columns to expenses

Revision ID: 0003_add_recurring_expenses
Revises: 0002_add_user_language
Create Date: 2026-05-27 00:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_add_recurring_expenses"
down_revision: str | None = "0002_add_user_language"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- new table: recurring_expenses ---
    op.create_table(
        "recurring_expenses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "description",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=False,
        ),
        sa.Column("day_of_month", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recurring_expenses_user_id",
        "recurring_expenses",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_recurring_expenses_category_id",
        "recurring_expenses",
        ["category_id"],
        unique=False,
    )

    # --- new columns on expenses ---
    op.add_column(
        "expenses",
        sa.Column("recurring_expense_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_expenses_recurring_expense_id",
        "expenses",
        ["recurring_expense_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_expenses_recurring_expense_id",
        "expenses",
        "recurring_expenses",
        ["recurring_expense_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "expenses",
        sa.Column(
            "is_recurring",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    # --- remove columns from expenses ---
    op.drop_constraint(
        "fk_expenses_recurring_expense_id",
        "expenses",
        type_="foreignkey",
    )
    op.drop_index("ix_expenses_recurring_expense_id", table_name="expenses")
    op.drop_column("expenses", "recurring_expense_id")
    op.drop_column("expenses", "is_recurring")

    # --- drop recurring_expenses table ---
    op.drop_index("ix_recurring_expenses_category_id", table_name="recurring_expenses")
    op.drop_index("ix_recurring_expenses_user_id", table_name="recurring_expenses")
    op.drop_table("recurring_expenses")
