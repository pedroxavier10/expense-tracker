"""Tool: leaderboard of categories by total spend in a date window."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import Session

from app.services import expense_service


class TopCategoriesInput(BaseModel):
    date_from: date | None = Field(default=None, description="Inclusive lower bound.")
    date_to: date | None = Field(default=None, description="Inclusive upper bound.")
    limit: int = Field(default=5, ge=1, le=50)


def top_categories(session: Session, user_id: UUID, payload: TopCategoriesInput) -> dict:
    return expense_service.get_top_categories(
        session, user_id, payload.date_from, payload.date_to, payload.limit
    )
