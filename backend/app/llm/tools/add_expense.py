"""Tool: add an expense from an LLM-parsed prompt.

Example prompt: "add 12.50€ lunch yesterday in food"

The LLM is responsible for resolving relative dates ("yesterday") and the
category slug *before* calling the tool. The tool itself does no NLP — it
just validates the structured input and writes to the database.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session

from app.schemas.expense import ExpenseCreate
from app.services import category_service, expense_service


class AddExpenseInput(ExpenseCreate):
    """Reuses ExpenseCreate so the schema stays a single source of truth.

    If the LLM should be allowed to pass a category *slug* instead of an id,
    extend this with a `category_slug: str | None` field and resolve it
    inside the handler.
    """


def add_expense(session: Session, user_id: UUID, payload: AddExpenseInput) -> dict:
    if not category_service.get_category(session, payload.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    expense = expense_service.create_expense(session, user_id, payload)
    return {
        "id": str(expense.id),
        "amount": str(expense.amount),
        "date": expense.expense_date.isoformat(),
        "description": expense.description,
        "category_id": str(expense.category_id),
        "message": "Expense recorded successfully.",
    }
