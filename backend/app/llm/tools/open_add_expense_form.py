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

from app.services import category_service, category_suggestion_service


class OpenAddExpenseFormInput(BaseModel):
    """All fields optional — the model fills in whatever it inferred."""

    # float avoids Decimal's lookahead-regex JSON Schema rejected by ECMA-262 validators (e.g. Groq)
    amount: float | None = Field(default=None, gt=0, description="Expense amount.")
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
        cat = category_service.get_category_by_slug(session, user_id, payload.category_slug)
        if cat:
            category_id = str(cat.id)
    if category_id is None and payload.description:
        # The model gave no (valid) category: fall back to what the user's own
        # corrections/history say. The user still reviews it in the form.
        suggestion = category_suggestion_service.suggest_category(
            session, user_id, payload.description
        )
        if suggestion:
            category_id = str(suggestion.category.id)

    # `amount` is a float on the input model (see note on the field above:
    # Decimal would emit a lookahead-regex JSON Schema that Groq rejects with a
    # 400). The float loses trailing-zero precision (23.00 -> 23.0), so we
    # quantize back to 2 decimals here to keep money in canonical "0.00" string
    # form for the wire / frontend prefill.
    prefill = {
        "amount": (
            str(Decimal(str(payload.amount)).quantize(Decimal("0.01")))
            if payload.amount is not None
            else None
        ),
        "expense_date": payload.expense_date.isoformat() if payload.expense_date else None,
        "description": payload.description,
        "category_id": category_id,
    }
    return {
        "action": "open_add_expense_form",
        "prefill": {k: v for k, v in prefill.items() if v is not None},
    }
