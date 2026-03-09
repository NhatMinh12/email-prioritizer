"""FastAPI dependency injection factories."""

import logging

import anthropic
import redis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.models import User
from app.services.auth_service import verify_access_token
from app.services.cache_service import CacheService
from app.services.claude_service import ClaudeService
from app.services.gmail_service import GmailService
from app.services.oauth_service import (
    OAuthError,
    build_credentials,
    refresh_credentials_if_expired,
)

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/callback")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate the current user from the JWT Bearer token.

    Raises:
        HTTPException 401: If the token is invalid, expired, or the user
            does not exist in the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_access_token(token)
        user_id = payload["sub"]
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def get_cache_service() -> CacheService:
    """Create a CacheService backed by the configured Redis instance."""
    redis_client = redis.from_url(settings.redis_url)
    return CacheService(redis_client=redis_client)


def get_claude_service() -> ClaudeService:
    """Create a ClaudeService backed by the Anthropic client."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return ClaudeService(client=client)


def get_gmail_service(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GmailService:
    """Create a GmailService with the current user's OAuth credentials."""
    try:
        credentials = build_credentials(current_user)
        credentials = refresh_credentials_if_expired(credentials, current_user, db)
    except OAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Gmail authentication required: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return GmailService(credentials=credentials)
