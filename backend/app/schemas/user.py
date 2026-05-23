"""User API schemas (request/response DTOs).

Kept separate from the ORM model so the public API contract can evolve
independently from the database shape.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload for creating a new user."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    """Public representation of a user. Never includes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    """OAuth2-style token response."""

    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """JSON login payload (alternative to OAuth2 form-data)."""

    email: EmailStr
    password: str
