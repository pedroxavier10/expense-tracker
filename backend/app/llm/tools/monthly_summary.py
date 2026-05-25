"""Tool: total + per-category breakdown for a given month."""

from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import Session

from app.services import expense_service


class MonthlySummaryInput(BaseModel):
    month: str = Field(
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Month in YYYY-MM format (e.g. '2026-05').",
    )


def monthly_summary(session: Session, user_id: UUID, payload: MonthlySummaryInput) -> dict:
    return expense_service.get_monthly_summary(session, user_id, payload.month)
