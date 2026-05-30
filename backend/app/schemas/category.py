"""Category API schemas."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CategoryRead(BaseModel):
    """Public representation of a category."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    icon: str | None = None
    is_active: bool = True


class CategoryCreate(BaseModel):
    """Payload for creating a category.

    The slug is generated server-side (see `slug_service`), so it is not part
    of the request.
    """

    name: str = Field(min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=10)


class CategoryUpdate(BaseModel):
    """Payload for updating a category.

    All fields optional: rename (`name`), change the icon, or restore an
    archived category (`is_active=True`). The slug is system-managed — it is
    regenerated when the name changes and is never set directly.
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=10)
    is_active: bool | None = None


class CategoryDeleteResult(BaseModel):
    """Result of a delete request: either hard-deleted or archived."""

    action: Literal["deleted", "archived"]
    category: CategoryRead | None = None
