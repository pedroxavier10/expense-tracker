from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.expense import ExpenseRead
from app.schemas.recurring_expense import (
    RecurringExpenseCreate,
    RecurringExpenseRead,
    RecurringExpenseUpdate,
)
from app.services import category_service, recurring_expense_service

router = APIRouter(prefix="/recurring-expenses", tags=["recurring-expenses"])


@router.get("", response_model=list[RecurringExpenseRead], summary="List recurring expense rules")
def list_recurring_expenses(
    session: SessionDep, current_user: CurrentUser
) -> list[RecurringExpenseRead]:
    rules = recurring_expense_service.list_recurring_expenses(session, current_user.id)
    return [RecurringExpenseRead.model_validate(r) for r in rules]


@router.post(
    "",
    response_model=RecurringExpenseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a recurring expense rule",
)
def create_recurring_expense(
    payload: RecurringExpenseCreate, session: SessionDep, current_user: CurrentUser
) -> RecurringExpenseRead:
    if not category_service.get_category(session, payload.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    rule = recurring_expense_service.create_recurring_expense(session, current_user.id, payload)
    return RecurringExpenseRead.model_validate(rule)


@router.get(
    "/{rule_id}",
    response_model=RecurringExpenseRead,
    summary="Get a recurring expense rule",
)
def get_recurring_expense(
    rule_id: UUID, session: SessionDep, current_user: CurrentUser
) -> RecurringExpenseRead:
    rule = recurring_expense_service.get_recurring_expense(session, current_user.id, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    return RecurringExpenseRead.model_validate(rule)


@router.patch(
    "/{rule_id}",
    response_model=RecurringExpenseRead,
    summary="Update a recurring expense rule",
)
def update_recurring_expense(
    rule_id: UUID,
    payload: RecurringExpenseUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> RecurringExpenseRead:
    if payload.category_id and not category_service.get_category(session, payload.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    rule = recurring_expense_service.update_recurring_expense(
        session, current_user.id, rule_id, payload
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    return RecurringExpenseRead.model_validate(rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a recurring expense rule",
)
def delete_recurring_expense(
    rule_id: UUID, session: SessionDep, current_user: CurrentUser
) -> None:
    deleted = recurring_expense_service.delete_recurring_expense(
        session, current_user.id, rule_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Recurring expense not found")


@router.post(
    "/{rule_id}/materialize-current-month",
    response_model=ExpenseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create the expense for the current month from a recurring rule",
)
def materialize_current_month(
    rule_id: UUID, session: SessionDep, current_user: CurrentUser
) -> ExpenseRead:
    rule = recurring_expense_service.get_recurring_expense(session, current_user.id, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Recurring expense not found")

    today = date.today()
    expense = recurring_expense_service.materialize_for_rule(session, rule, today.year, today.month)
    if expense is None:
        raise HTTPException(
            status_code=409,
            detail="Expense for the current month already exists or rule is inactive",
        )
    return ExpenseRead.model_validate(expense)
