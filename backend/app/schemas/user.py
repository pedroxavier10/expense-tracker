"""User API schemas (request/response DTOs).

Kept separate from the ORM model so the public API contract can evolve
independently from the database shape.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Language = Literal["en", "pt"]


class UserRead(BaseModel):
    """Public representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    is_active: bool
    language: Language
    created_at: datetime


class UserUpdate(BaseModel):
    """Partial update of user preferences. All fields optional."""

    language: Language | None = None


class Token(BaseModel):
    """OAuth2-style token response."""

    access_token: str
    token_type: str = "bearer"


class GoogleLoginRequest(BaseModel):
    """Google Identity Services credential (an ID token JWT)."""

    credential: str = Field(min_length=1, max_length=4096)


class AuthConfig(BaseModel):
    """Public auth configuration so the frontend knows which login to show."""

    google_enabled: bool
    google_client_id: str | None
