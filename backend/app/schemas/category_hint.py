"""Schemas for learned category hints ("O que aprendi" screen)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.category import CategoryRead


class CategoryHintRead(BaseModel):
    """A learned "description -> category" preference.

    `category.is_active` is False when the category was archived; such hints
    are kept but ignored by suggestions until the category is restored.
    """

    id: UUID
    description: str
    category: CategoryRead
    hit_count: int
    last_used_at: datetime


class CategoryHintUpdate(BaseModel):
    """Change the category a learned description maps to."""

    category_id: UUID
