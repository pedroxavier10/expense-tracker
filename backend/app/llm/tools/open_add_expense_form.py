"""Tool: signal the frontend to open the "add expense" modal pre-filled.

This is a *client action* tool — it does not write to the database. The
handler validates whatever the model managed to extract from the user's
message and returns a payload that the frontend interprets as a UI intent.

The model should prefer this over `add_expense` when it doesn't have all
required fields, or when the user explicitly asks to "open the form".
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import Session

from app.services import category_service


class OpenAddExpenseFormInput(BaseModel):
    """All fields optional — the model fills in whatever it inferred."""

    amount: Decimal | None = Field(default=None, gt=0, description="Expense amount.")
    expense_date: date | None = Field(default=None, description="Date of the expense.")
    description: str | None = Field(default=None, max_length=500)
    category_slug: str | None = Field(
        default=None,
        description="Category slug (e.g. 'food'). Resolved to the corresponding id.",
    )


def open_add_expense_form(
    session: Session, user_id: UUID, payload: OpenAddExpenseFormInput
) -> dict:
    category_id: str | None = None
    if payload.category_slug:
        cat = category_service.get_category_by_slug(session, payload.category_slug)
        if cat:
            category_id = str(cat.id)

    prefill = {
        "amount": str(payload.amount) if payload.amount is not None else None,
        "expense_date": payload.expense_date.isoformat() if payload.expense_date else None,
        "description": payload.description,
        "category_id": category_id,
    }
    return {
        "action": "open_add_expense_form",
        "prefill": {k: v for k, v in prefill.items() if v is not None},
    }
