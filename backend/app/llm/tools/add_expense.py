"""Tool: add an expense from an LLM-parsed prompt.

Example prompt: "add 12.50€ lunch yesterday in food"

The LLM is responsible for resolving relative dates ("yesterday") and the
category slug *before* calling the tool. The tool itself does no NLP — it
just validates the structured input and writes to the database.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.llm.registry import FOLLOWUP_ACTION_KEY
from app.schemas.expense import ExpenseCreate
from app.schemas.recurring_suggestion import RecurringSuggestionRead
from app.services import category_service, expense_service, recurring_suggestion_service


class AddExpenseInput(BaseModel):
    """Input model for the add_expense LLM tool.

    Uses float for amount to avoid Decimal's lookahead-regex JSON Schema,
    which is rejected by ECMA-262-strict validators (e.g. Groq). Conversion
    to Decimal happens inside the handler before calling the service.
    """

    amount: float = Field(gt=0)
    expense_date: date
    description: str = Field(min_length=1, max_length=500)
    category_id: UUID


def add_expense(session: Session, user_id: UUID, payload: AddExpenseInput) -> dict:
    if not category_service.get_category(session, user_id, payload.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    expense_data = ExpenseCreate(
        amount=Decimal(str(payload.amount)),
        expense_date=payload.expense_date,
        description=payload.description,
        category_id=payload.category_id,
    )
    expense = expense_service.create_expense(session, user_id, expense_data)
    result: dict = {
        "id": str(expense.id),
        "amount": str(expense.amount),
        "date": expense.expense_date.isoformat(),
        "description": expense.description,
        "category_id": str(expense.category_id),
        "message": "Expense recorded successfully.",
    }

    # Same trigger as POST /expenses: if this expense completes a monthly
    # pattern, the app itself asks the user (in a modal) whether to make it
    # recurring. The model only needs to know that this is being handled.
    suggestion = recurring_suggestion_service.find_for_expense(session, user_id, expense)
    if suggestion is not None:
        result["recurring_suggestion_shown"] = True
        result["message"] = (
            "Expense recorded successfully. The app is now asking the user whether to "
            "turn it into a recurring expense — do not ask about it yourself."
        )
        result[FOLLOWUP_ACTION_KEY] = {
            "action": "suggest_recurring_expense",
            "recurring_suggestion": RecurringSuggestionRead.model_validate(suggestion).model_dump(
                mode="json"
            ),
        }
    return result
