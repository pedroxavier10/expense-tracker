"""Category endpoints: per-user CRUD.

Categories belong to the authenticated user. The slug is generated server-side
(see `slug_service`), so it is never accepted from the client. Deleting a
category that is still in use archives it instead of removing it.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.category import (
    CategoryCreate,
    CategoryDeleteResult,
    CategoryRead,
    CategoryUpdate,
)
from app.services import category_service, slug_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead], summary="List the user's categories")
def list_categories(
    session: SessionDep,
    current_user: CurrentUser,
    include_inactive: bool = Query(
        default=False, description="Include archived (inactive) categories"
    ),
) -> list[CategoryRead]:
    categories = category_service.list_categories(
        session, current_user.id, include_inactive=include_inactive
    )
    return [CategoryRead.model_validate(c) for c in categories]


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category (slug auto-generated)",
)
async def create_category(
    payload: CategoryCreate, session: SessionDep, current_user: CurrentUser
) -> CategoryRead:
    slug = await slug_service.generate_category_slug(
        session, current_user.id, payload.name
    )
    category = category_service.create_category(
        session, current_user.id, slug=slug, name=payload.name, icon=payload.icon
    )
    return CategoryRead.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryRead, summary="Update a category")
async def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> CategoryRead:
    category = await category_service.update_category(
        session, current_user.id, category_id, payload
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryRead.model_validate(category)


@router.delete(
    "/{category_id}",
    response_model=CategoryDeleteResult,
    summary="Delete a category (archived instead if it is still in use)",
)
def delete_category(
    category_id: UUID, session: SessionDep, current_user: CurrentUser
) -> CategoryDeleteResult:
    result = category_service.delete_or_archive_category(
        session, current_user.id, category_id
    )
    if not result:
        raise HTTPException(status_code=404, detail="Category not found")
    return result
