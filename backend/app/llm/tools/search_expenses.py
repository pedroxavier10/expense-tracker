"""Tool: search expenses by natural-language-derived filters.

The LLM extracts structured filters from the user prompt and calls this tool.
The actual querying is delegated to `expense_service.list_expenses`, the same
function the REST API uses — guaranteeing consistent behaviour.

NOTE: Not wired into a chat endpoint yet. This is here so the contract is
visible and unit-testable from day one.
"""

from uuid import UUID

from sqlmodel import Session

from app.schemas.expense import ExpenseFilters
from app.services import expense_service


def search_expenses(session: Session, user_id: UUID, payload: ExpenseFilters) -> dict:
    """Search expenses for the authenticated user.

    Returns a JSON-serializable dict so it can be sent back to the LLM as a
    tool result.
    """
    items, total = expense_service.list_expenses(session, user_id, payload)
    return {
        "total": total,
        "count_returned": len(items),
        "items": [
            {
                "id": str(item.id),
                "amount": str(item.amount),
                "date": item.expense_date.isoformat(),
                "description": item.description,
                "category_id": str(item.category_id),
            }
            for item in items
        ],
    }
