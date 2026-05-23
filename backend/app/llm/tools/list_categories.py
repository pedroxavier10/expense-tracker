"""Tool: list available expense categories.

The LLM needs this to resolve human-friendly category names ("food",
"transport") into the UUIDs that `add_expense` and `search_expenses` expect.
"""

from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session

from app.services import category_service


class ListCategoriesInput(BaseModel):
    """No arguments — returns every category."""


def list_categories(session: Session, user_id: UUID, payload: ListCategoriesInput) -> dict:
    cats = category_service.list_categories(session)
    return {
        "categories": [
            {
                "id": str(c.id),
                "slug": c.slug,
                "name": c.name,
                "icon": c.icon,
            }
            for c in cats
        ]
    }
