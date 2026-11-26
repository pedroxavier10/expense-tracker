"""Learned category hints: list, re-point or forget what the app learned
from the user's category corrections (the "O que aprendi" screen)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep
from app.models.category import Category
from app.models.category_hint import CategoryHint
from app.schemas.category import CategoryRead
from app.schemas.category_hint import CategoryHintRead, CategoryHintUpdate
from app.services import category_service, category_suggestion_service

router = APIRouter(prefix="/category-hints", tags=["category-hints"])


def _to_read(hint: CategoryHint, category: Category) -> CategoryHintRead:
    return CategoryHintRead(
        id=hint.id,
        description=hint.description,
        category=CategoryRead.model_validate(category),
        hit_count=hint.hit_count,
        last_used_at=hint.last_used_at,
    )


@router.get("", response_model=list[CategoryHintRead], summary="List learned category hints")
def list_hints(session: SessionDep, current_user: CurrentUser) -> list[CategoryHintRead]:
    return [
        _to_read(hint, category)
        for hint, category in category_suggestion_service.list_hints(session, current_user.id)
    ]


@router.patch("/{hint_id}", response_model=CategoryHintRead, summary="Change a hint's category")
def update_hint(
    hint_id: UUID,
    payload: CategoryHintUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> CategoryHintRead:
    category = category_service.get_category(session, current_user.id, payload.category_id)
    if category is None or not category.is_active:
        raise HTTPException(status_code=404, detail="Category not found")
    result = category_suggestion_service.update_hint_category(
        session, current_user.id, hint_id, category
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Hint not found")
    return _to_read(*result)


@router.delete(
    "/{hint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Forget a learned hint",
)
def delete_hint(hint_id: UUID, session: SessionDep, current_user: CurrentUser) -> None:
    if not category_suggestion_service.delete_hint(session, current_user.id, hint_id):
        raise HTTPException(status_code=404, detail="Hint not found")
