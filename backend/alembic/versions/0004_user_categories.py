"""Make categories per-user (add user_id + is_active, scope slug uniqueness)

Revision ID: 0004_user_categories
Revises: 0003_add_recurring_expenses
Create Date: 2026-05-30 00:00:00

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_user_categories"
down_revision: Union[str, None] = "0003_add_recurring_expenses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _partition_categories_per_user() -> None:
    """Turn the previously global categories into per-user sets.

    Categories used to be shared across all users. Now each user owns their own
    set, so every existing user must end up with a full copy of the categories,
    and their expenses/recurring rules must point at *their* copy.

    Approach (correct for any number of users):
      - The first user keeps the original category rows (no re-pointing needed).
      - Every other user gets a fresh copy of each category, and their expenses
        and recurring rules are re-pointed from the original to their copy.
    If there are no users, the orphan global categories are deleted (the seed
    recreates them per-user on first run).
    """
    bind = op.get_bind()

    cats = bind.execute(sa.text("SELECT id, slug, name, icon FROM categories")).fetchall()
    if not cats:
        return

    user_ids = [r[0] for r in bind.execute(sa.text("SELECT id FROM users")).fetchall()]
    if not user_ids:
        bind.execute(sa.text("DELETE FROM categories"))
        return

    # First user owns the originals.
    bind.execute(
        sa.text("UPDATE categories SET user_id = :uid WHERE user_id IS NULL"),
        {"uid": user_ids[0]},
    )

    # Every other user gets their own copy + re-pointed references.
    for uid in user_ids[1:]:
        for old_id, slug, name, icon in cats:
            new_id = uuid.uuid4()
            bind.execute(
                sa.text(
                    "INSERT INTO categories (id, user_id, slug, name, icon, is_active) "
                    "VALUES (:id, :uid, :slug, :name, :icon, true)"
                ),
                {"id": new_id, "uid": uid, "slug": slug, "name": name, "icon": icon},
            )
            bind.execute(
                sa.text(
                    "UPDATE expenses SET category_id = :new "
                    "WHERE user_id = :uid AND category_id = :old"
                ),
                {"new": new_id, "uid": uid, "old": old_id},
            )
            bind.execute(
                sa.text(
                    "UPDATE recurring_expenses SET category_id = :new "
                    "WHERE user_id = :uid AND category_id = :old"
                ),
                {"new": new_id, "uid": uid, "old": old_id},
            )


def upgrade() -> None:
    # 1. Add the new columns (user_id nullable for now, backfilled below).
    op.add_column("categories", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.add_column(
        "categories",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # 2. Drop the global-unique slug index BEFORE backfilling: the per-user
    #    partition inserts duplicate slugs (one "food" per user), which the old
    #    unique index would reject.
    op.drop_index("ix_categories_slug", table_name="categories")
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=False)

    # 3. Partition categories per user, then enforce NOT NULL.
    _partition_categories_per_user()
    op.alter_column("categories", "user_id", existing_type=sa.Uuid(), nullable=False)

    # 4. Remaining indexes, FK and the per-user unique constraint.
    op.create_index("ix_categories_user_id", "categories", ["user_id"], unique=False)
    op.create_index("ix_categories_is_active", "categories", ["is_active"], unique=False)
    op.create_foreign_key("fk_categories_user_id", "categories", "users", ["user_id"], ["id"])
    op.create_unique_constraint("uq_categories_user_slug", "categories", ["user_id", "slug"])


def _merge_duplicate_slugs() -> None:
    """Collapse per-user category copies back to one row per slug.

    The upgrade created duplicate slugs (one per user). Restoring the global
    unique slug index requires a single row per slug, so for each slug we keep
    one canonical row, re-point all expenses/recurring rules to it, and delete
    the duplicates. This is lossy (per-user customizations are merged) but is
    the only way to return to the global-category model.
    """
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, slug FROM categories ORDER BY slug, id")).fetchall()
    canonical: dict[str, object] = {}
    for cid, slug in rows:
        keep = canonical.get(slug)
        if keep is None:
            canonical[slug] = cid
            continue
        bind.execute(
            sa.text("UPDATE expenses SET category_id = :keep WHERE category_id = :dup"),
            {"keep": keep, "dup": cid},
        )
        bind.execute(
            sa.text("UPDATE recurring_expenses SET category_id = :keep WHERE category_id = :dup"),
            {"keep": keep, "dup": cid},
        )
        bind.execute(sa.text("DELETE FROM categories WHERE id = :dup"), {"dup": cid})


def downgrade() -> None:
    op.drop_constraint("uq_categories_user_slug", "categories", type_="unique")
    op.drop_constraint("fk_categories_user_id", "categories", type_="foreignkey")
    op.drop_index("ix_categories_is_active", table_name="categories")
    op.drop_index("ix_categories_user_id", table_name="categories")

    # Deduplicate slugs before restoring the global-unique index.
    _merge_duplicate_slugs()
    op.drop_index("ix_categories_slug", table_name="categories")
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)

    op.drop_column("categories", "is_active")
    op.drop_column("categories", "user_id")
