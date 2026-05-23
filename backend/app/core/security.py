"""Security primitives: password hashing and JWT token handling.

Kept intentionally small. For a single-user personal app we use HS256 JWTs and
bcrypt for password hashing. If the app ever grows multi-tenant, swap HS256
for RS256 and consider a refresh-token rotation strategy.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The token subject (typically the user id as string).
        expires_delta: Optional custom expiration. Defaults to the configured
            access_token_expire_minutes.
    """
    settings = get_settings()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode: dict[str, Any] = {"exp": expire, "sub": subject}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> str | None:
    """Decode and validate a JWT. Returns the subject or None if invalid."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload.get("sub")
    except JWTError:
        return None
