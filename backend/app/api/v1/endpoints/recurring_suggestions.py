"""Recurring-expense suggestions: the user's answer to "make this recurring?".

Suggestions themselves are returned by POST /expenses (and the chat's
add_expense tool) when a just-registered expense completes a monthly pattern.
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.recurring_expense import RecurringExpenseRead
from app.schemas.recurring_suggestion import (
    RecurringSuggestionAccept,
    RecurringSuggestionAcceptResult,
    RecurringSuggestionKey,
)
from app.services import category_service, recurring_suggestion_service

router = APIRouter(prefix="/recurring-suggestions", tags=["recurring-suggestions"])


@router.post(
    "/accept",
    response_model=RecurringSuggestionAcceptResult,
    status_code=status.HTTP_201_CREATED,
    summary="Create the recurring rule and link the pattern's past expenses to it",
)
def accept_suggestion(
    payload: RecurringSuggestionAccept, session: SessionDep, current_user: CurrentUser
) -> RecurringSuggestionAcceptResult:
    category = category_service.get_category(session, current_user.id, payload.rule.category_id)
    if category is None or not category.is_active:
        raise HTTPException(status_code=404, detail="Category not found")
    result = recurring_suggestion_service.accept(
        session, current_user.id, payload.pattern_key, payload.rule
    )
    if result is None:
        raise HTTPException(status_code=409, detail="This suggestion no longer applies")
    return RecurringSuggestionAcceptResult(
        rule=RecurringExpenseRead.model_validate(result.rule),
        linked_expenses=result.linked_expenses,
        current_month_covered=result.current_month_covered,
    )


@router.post(
    "/dismiss",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Decline a suggestion; the pattern is counted from zero again",
)
def dismiss_suggestion(
    payload: RecurringSuggestionKey, session: SessionDep, current_user: CurrentUser
) -> None:
    recurring_suggestion_service.dismiss(session, current_user.id, payload.pattern_key)
