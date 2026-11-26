"""Expense endpoints: full CRUD plus filtered listing."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.category import CategoryRead
from app.schemas.category_suggestion import CategorySuggestionRead
from app.schemas.expense import (
    AnnualSummaryResponse,
    ExpenseCreate,
    ExpenseFilters,
    ExpenseListResponse,
    ExpenseRead,
    ExpenseUpdate,
    MonthlySummaryResponse,
)
from app.services import category_service, category_suggestion_service, expense_service

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("", response_model=ExpenseListResponse, summary="List expenses with filters")
def list_expenses(
    session: SessionDep,
    current_user: CurrentUser,
    category_id: Annotated[UUID | None, Query(description="Filter by category id")] = None,
    category_slug: Annotated[str | None, Query(description="Filter by category slug")] = None,
    date_from: Annotated[date | None, Query(description="Inclusive lower bound")] = None,
    date_to: Annotated[date | None, Query(description="Inclusive upper bound")] = None,
    month: Annotated[
        str | None,
        Query(
            description="YYYY-MM convenience filter (mutually exclusive with date_from/date_to)",
            pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        ),
    ] = None,
    description_contains: Annotated[
        str | None, Query(description="Case-insensitive substring match")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
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
    if not category_service.get_category(session, current_user.id, payload.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    expense = expense_service.create_expense(session, current_user.id, payload)
    return ExpenseRead.model_validate(expense)


@router.get(
    "/category-suggestion",
    response_model=CategorySuggestionRead,
    responses={204: {"description": "No confident suggestion"}},
    summary="Suggest a category for a description (learned corrections + history)",
)
def suggest_category(
    session: SessionDep,
    current_user: CurrentUser,
    description: Annotated[str, Query(min_length=1, max_length=500)],
) -> CategorySuggestionRead | Response:
    suggestion = category_suggestion_service.suggest_category(session, current_user.id, description)
    if suggestion is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return CategorySuggestionRead(
        category=CategoryRead.model_validate(suggestion.category),
        confidence=suggestion.confidence,
        source=suggestion.source,
    )


@router.get(
    "/summary",
    response_model=MonthlySummaryResponse,
    summary="Monthly spending summary (totals by category)",
)
def get_monthly_summary(
    session: SessionDep,
    current_user: CurrentUser,
    month: Annotated[
        str,
        Query(description="Month in YYYY-MM format", pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    ],
) -> MonthlySummaryResponse:
    result = expense_service.get_monthly_summary(session, current_user.id, month)
    return MonthlySummaryResponse.model_validate(result)


@router.get(
    "/annual-summary",
    response_model=AnnualSummaryResponse,
    summary="Annual spending summary (monthly totals + breakdown by category)",
)
def get_annual_summary(
    session: SessionDep,
    current_user: CurrentUser,
    year: Annotated[int, Query(description="Calendar year, e.g. 2026", ge=2000, le=2100)],
) -> AnnualSummaryResponse:
    result = expense_service.get_annual_summary(session, current_user.id, year)
    return AnnualSummaryResponse.model_validate(result)


@router.get("/{expense_id}", response_model=ExpenseRead, summary="Get an expense by id")
def get_expense(expense_id: UUID, session: SessionDep, current_user: CurrentUser) -> ExpenseRead:
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
    if payload.category_id and not category_service.get_category(
        session, current_user.id, payload.category_id
    ):
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
def delete_expense(expense_id: UUID, session: SessionDep, current_user: CurrentUser) -> None:
    deleted = expense_service.delete_expense(session, current_user.id, expense_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Expense not found")
