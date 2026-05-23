"""Category endpoints.

Read-only for now: categories are managed by the seed script. Adding a POST
later (for user-defined categories) is straightforward.
"""

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.schemas.category import CategoryRead
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead], summary="List all categories")
def list_categories(session: SessionDep, _: CurrentUser) -> list[CategoryRead]:
    categories = category_service.list_categories(session)
    return [CategoryRead.model_validate(c) for c in categories]
