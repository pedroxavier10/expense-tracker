from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryRead


class RecurringExpenseCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str = Field(min_length=1, max_length=500)
    day_of_month: int = Field(ge=1, le=31)
    category_id: UUID
    end_date: date | None = None
    is_active: bool = True


class RecurringExpenseUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    category_id: UUID | None = None
    end_date: date | None = None
    is_active: bool | None = None


class RecurringExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    description: str
    day_of_month: int
    is_active: bool
    end_date: date | None
    category: CategoryRead
    created_at: datetime
    updated_at: datetime
