"""Schemas for learned category suggestions."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.category import CategoryRead


class CategorySuggestionRead(BaseModel):
    """Suggested category for an expense description.

    `source` tells where it came from: `learned` = an explicit user correction
    (CategoryHint), `history` = the categories of similar past expenses.
    `confidence` is in [0, 1].
    """

    category: CategoryRead
    confidence: float
    source: Literal["learned", "history"]
