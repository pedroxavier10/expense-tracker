"""API v1 router. Mounts all endpoint modules under /api/v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, categories, expenses

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(expenses.router)
