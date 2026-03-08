"""JWT authentication service."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger(__name__)


def create_access_token(user_id: uuid.UUID, email: str) -> str:
    """Create a JWT access token for a user.

    Args:
        user_id: The user's UUID.
        email: The user's email address.

    Returns:
        Encoded JWT string.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def verify_access_token(token: str) -> dict:
    """Verify and decode a JWT access token.

    Args:
        token: The JWT string to verify.

    Returns:
        Decoded payload dict with 'sub' (user_id) and 'email'.

    Raises:
        JWTError: If the token is invalid, expired, or missing required claims.
    """
    payload = jwt.decode(
        token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )
    user_id = payload.get("sub")
    email = payload.get("email")
    if user_id is None or email is None:
        raise JWTError("Token missing required claims")
    return payload
