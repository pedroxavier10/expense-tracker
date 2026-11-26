"""Switch users to Google sign-in (add google_sub, drop hashed_password)

Revision ID: 0005_google_auth
Revises: 0004_user_categories
Create Date: 2026-11-25 00:00:00

Passwords are no longer used: users sign in with Google (or the dev login in
development). Existing users keep their data; they are linked to their Google
account on first sign-in when the verified Google email matches `users.email`.

Downgrade restores `hashed_password` as a nullable column, but the original
hashes are gone — users would need new passwords set manually.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_google_auth"
down_revision: str | None = "0004_user_categories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("google_sub", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    )
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)
    # Emails are now compared case-insensitively (stored lowercase).
    op.execute("UPDATE users SET email = lower(email)")
    op.drop_column("users", "hashed_password")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("hashed_password", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    )
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "google_sub")
