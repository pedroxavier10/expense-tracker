"""SQLModel ORM models.

Importing every model here ensures they are all registered on the SQLModel
metadata, which Alembic needs for autogenerate to work.
"""

from app.models.category import Category
from app.models.expense import Expense
from app.models.user import User

__all__ = ["Category", "Expense", "User"]
