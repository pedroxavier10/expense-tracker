"""Add language column to users

Revision ID: 0002_add_user_language
Revises: 0001_initial
Create Date: 2026-05-27 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_add_user_language"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "language",
            sqlmodel.sql.sqltypes.AutoString(length=8),
            nullable=False,
            server_default="en",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "language")
