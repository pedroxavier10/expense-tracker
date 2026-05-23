"""Tool registry. Add new tools here.

Importing this module populates `REGISTRY` with every tool the LLM layer
exposes. Provider adapters (future work) iterate over `REGISTRY` to build
their tool schemas.
"""

from app.llm.registry import Tool
from app.llm.tools.add_expense import AddExpenseInput, add_expense
from app.llm.tools.search_expenses import search_expenses
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
    "add_expense": Tool(
        name="add_expense",
        description=(
            "Record a new expense for the authenticated user. The caller must "
            "have already resolved any relative dates and the category id."
        ),
        input_model=AddExpenseInput,
        handler=add_expense,
    ),
}


def get_tool(name: str) -> Tool | None:
    """Look up a tool by name. Returns None if not registered."""
    return REGISTRY.get(name)
