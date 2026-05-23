"""Category API schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CategoryRead(BaseModel):
    """Public representation of a category."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    icon: str | None = None


class CategoryCreate(BaseModel):
    """Payload for creating a category (admin/seed use)."""

    slug: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=10)
