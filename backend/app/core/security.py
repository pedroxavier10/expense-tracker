"""Security primitives: Google ID token verification and app JWT handling.

Users authenticate with Google; the backend verifies the Google ID token and
then issues its own short HS256 JWT, so the rest of the API only ever deals
with app tokens. No passwords are stored.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.core.config import get_settings

# Reused across calls: the transport caches Google's public signing certs.
_google_request = google_requests.Request()


@dataclass(frozen=True)
class GoogleIdentity:
    """The verified subset of a Google ID token we rely on."""

    sub: str
    email: str


def verify_google_id_token(token: str, client_id: str) -> GoogleIdentity | None:
    """Verify a Google ID token and return the identity, or None if invalid.

    `verify_oauth2_token` checks the signature, expiry, issuer and that the
    audience is our client id. We additionally require a verified email.
    """
    try:
        claims = google_id_token.verify_oauth2_token(token, _google_request, client_id)
    except ValueError:
        return None
    sub = claims.get("sub")
    email = claims.get("email")
    if not sub or not email or claims.get("email_verified") is not True:
        return None
    return GoogleIdentity(sub=sub, email=email.lower())


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
    except jwt.exceptions.InvalidTokenError:
        return None
