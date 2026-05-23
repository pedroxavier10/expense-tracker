"""Expense endpoints: full CRUD plus filtered listing."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseFilters,
    ExpenseListResponse,
    ExpenseRead,
    ExpenseUpdate,
)
from app.services import category_service, expense_service

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("", response_model=ExpenseListResponse, summary="List expenses with filters")
def list_expenses(
    session: SessionDep,
    current_user: CurrentUser,
    category_id: UUID | None = Query(default=None, description="Filter by category id"),
    category_slug: str | None = Query(default=None, description="Filter by category slug"),
    date_from: date | None = Query(default=None, description="Inclusive lower bound"),
    date_to: date | None = Query(default=None, description="Inclusive upper bound"),
    month: str | None = Query(
        default=None,
        description="YYYY-MM convenience filter (mutually exclusive with date_from/date_to)",
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
    ),
    description_contains: str | None = Query(
        default=None, description="Case-insensitive substring match"
    ),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ExpenseListResponse:
    """List the current user's expenses with optional filtering and pagination."""
    try:
        filters = ExpenseFilters(
            category_id=category_id,
            category_slug=category_slug,
            date_from=date_from,
            date_to=date_to,
            month=month,
            description_contains=description_contains,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    items, total = expense_service.list_expenses(session, current_user.id, filters)
    return ExpenseListResponse(
        items=[ExpenseRead.model_validate(e) for e in items],
        total=total,
        limit=filters.limit,
        offset=filters.offset,
    )


@router.post(
    "",
    response_model=ExpenseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an expense",
)
def create_expense(
    payload: ExpenseCreate, session: SessionDep, current_user: CurrentUser
) -> ExpenseRead:
    if not category_service.get_category(session, payload.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    expense = expense_service.create_expense(session, current_user.id, payload)
    return ExpenseRead.model_validate(expense)


@router.get("/{expense_id}", response_model=ExpenseRead, summary="Get an expense by id")
def get_expense(
    expense_id: UUID, session: SessionDep, current_user: CurrentUser
) -> ExpenseRead:
    expense = expense_service.get_expense(session, current_user.id, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return ExpenseRead.model_validate(expense)


@router.patch("/{expense_id}", response_model=ExpenseRead, summary="Update an expense")
def update_expense(
    expense_id: UUID,
    payload: ExpenseUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> ExpenseRead:
    if payload.category_id and not category_service.get_category(session, payload.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    expense = expense_service.update_expense(session, current_user.id, expense_id, payload)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return ExpenseRead.model_validate(expense)


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an expense",
)
def delete_expense(
    expense_id: UUID, session: SessionDep, current_user: CurrentUser
) -> None:
    deleted = expense_service.delete_expense(session, current_user.id, expense_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Expense not found")
