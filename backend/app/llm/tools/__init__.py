"""Tool registry. Add new tools here.

Importing this module populates `REGISTRY` with every tool the LLM layer
exposes. Provider adapters iterate over `REGISTRY` to build their tool schemas.
"""

from app.llm.registry import Tool
from app.llm.tools.add_expense import AddExpenseInput, add_expense
from app.llm.tools.monthly_summary import MonthlySummaryInput, monthly_summary
from app.llm.tools.open_add_expense_form import (
    OpenAddExpenseFormInput,
    open_add_expense_form,
)
from app.llm.tools.search_expenses import search_expenses
from app.llm.tools.top_categories import TopCategoriesInput, top_categories
from app.schemas.expense import ExpenseFilters

REGISTRY: dict[str, Tool] = {
    "search_expenses": Tool(
        name="search_expenses",
        description=(
            "Search the authenticated user's expenses using structured filters: "
            "category id or slug, date range, specific month (YYYY-MM), or a "
            "description substring. Returns the matching expenses and a total count."
        ),
        input_model=ExpenseFilters,
        handler=search_expenses,
    ),
    "monthly_summary": Tool(
        name="monthly_summary",
        description=(
            "Return the total spend and per-category breakdown for a given month "
            "(YYYY-MM). Use this for questions like 'how much did I spend in April?' "
            "or 'where did my money go last month?'."
        ),
        input_model=MonthlySummaryInput,
        handler=monthly_summary,
    ),
    "top_categories": Tool(
        name="top_categories",
        description=(
            "Return the top N categories by total spend in a date window (both "
            "bounds optional). Use this for questions like 'where am I spending "
            "the most this year?'."
        ),
        input_model=TopCategoriesInput,
        handler=top_categories,
    ),
    "add_expense": Tool(
        name="add_expense",
        description=(
            "Record a new expense for the authenticated user. Only call this when "
            "you have a concrete amount, expense_date, description and category_id. "
            "If any required field is missing or uncertain, prefer "
            "open_add_expense_form so the user can confirm in the UI."
        ),
        input_model=AddExpenseInput,
        handler=add_expense,
    ),
    "open_add_expense_form": Tool(
        name="open_add_expense_form",
        description=(
            "Ask the frontend to open the 'add expense' modal pre-filled with "
            "whatever values you managed to extract. Use this when the user "
            "wants to add an expense but you are missing fields, or when they "
            "ask you to 'open the form'. Does NOT write to the database."
        ),
        input_model=OpenAddExpenseFormInput,
        handler=open_add_expense_form,
    ),
}


def get_tool(name: str) -> Tool | None:
    """Look up a tool by name. Returns None if not registered."""
    return REGISTRY.get(name)
