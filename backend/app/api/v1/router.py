"""API v1 router. Mounts all endpoint modules under /api/v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    categories,
    category_hints,
    chat,
    expenses,
    import_export,
    recurring_expenses,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(category_hints.router)
api_router.include_router(expenses.router)
api_router.include_router(recurring_expenses.router)
api_router.include_router(import_export.router)
api_router.include_router(chat.router)
