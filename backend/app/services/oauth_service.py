"""Google OAuth2 service for token exchange, credential building, and refresh."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import requests as http_requests
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)

GOOGLE_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


class OAuthError(Exception):
    """Raised when OAuth operations fail."""


@dataclass
class OAuthTokens:
    """Result of a successful OAuth token exchange."""

    access_token: str
    refresh_token: str
    expiry: Optional[datetime]
    email: str


def _build_client_config() -> dict:
    """Build the OAuth client config dict from app settings."""
    return {
        "web": {
            "client_id": settings.gmail_client_id,
            "client_secret": settings.gmail_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.gmail_redirect_uri],
        }
    }


def exchange_code_for_tokens(code: str) -> OAuthTokens:
    """Exchange an OAuth authorization code for access and refresh tokens.

    Args:
        code: The authorization code from Google's OAuth callback.

    Returns:
        OAuthTokens with access_token, refresh_token, expiry, and email.

    Raises:
        OAuthError: If the code exchange fails or email cannot be extracted.
    """
    try:
        flow = Flow.from_client_config(
            _build_client_config(),
            scopes=GOOGLE_OAUTH_SCOPES,
            redirect_uri=settings.gmail_redirect_uri,
        )
        flow.fetch_token(code=code)
    except Exception as exc:
        logger.error("OAuth token exchange failed: %s", exc)
        raise OAuthError(f"Failed to exchange authorization code: {exc}") from exc

    credentials = flow.credentials

    if not credentials.refresh_token:
        raise OAuthError(
            "No refresh token received. Ensure prompt=consent is set in the authorization URL."
        )

    # Extract email: prefer id_token, fall back to userinfo endpoint.
    # id_token can be None when google-auth can't decode the JWT
    # (missing optional crypto deps, library version mismatch, etc.).
    email = None
    id_token_data = credentials.id_token
    if id_token_data and isinstance(id_token_data, dict):
        email = id_token_data.get("email")

    if not email:
        logger.info("id_token unavailable or missing email; falling back to userinfo endpoint")
        try:
            resp = http_requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {credentials.token}"},
                timeout=10,
            )
            resp.raise_for_status()
            email = resp.json().get("email")
        except Exception as exc:
            logger.error("Userinfo request failed: %s", exc)
            raise OAuthError("Failed to determine user email.") from exc

    if not email:
        raise OAuthError("Email not found in token response or userinfo.")

    return OAuthTokens(
        access_token=credentials.token,
        refresh_token=credentials.refresh_token,
        expiry=credentials.expiry,
        email=email,
    )


def build_credentials(user: "User") -> Credentials:  # noqa: F821
    """Build Google OAuth Credentials from a user's stored tokens.

    Args:
        user: User model instance with OAuth token fields.

    Returns:
        A google.oauth2.credentials.Credentials object.

    Raises:
        OAuthError: If the user has no refresh token (re-auth required).
    """
    if not user.oauth_refresh_token:
        raise OAuthError("User has no OAuth credentials. Re-authentication required.")

    # Google's auth library compares expiry against a naive utcnow(),
    # so we must strip timezone info to avoid "can't compare offset-naive
    # and offset-aware datetimes" TypeError.
    expiry = user.oauth_token_expiry
    if expiry is not None and expiry.tzinfo is not None:
        expiry = expiry.replace(tzinfo=None)

    return Credentials(
        token=user.oauth_access_token,
        refresh_token=user.oauth_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
        expiry=expiry,
    )


def refresh_credentials_if_expired(
    credentials: Credentials,
    user: "User",  # noqa: F821
    db: Session,
) -> Credentials:
    """Refresh the credentials if the access token has expired.

    If a refresh occurs, the new access token and expiry are persisted
    back to the database.

    Args:
        credentials: The Google OAuth credentials to check/refresh.
        user: The User model instance to update if refresh occurs.
        db: SQLAlchemy session for persisting updated tokens.

    Returns:
        The (potentially refreshed) Credentials object.

    Raises:
        OAuthError: If the refresh fails (e.g., revoked refresh token).
    """
    if not credentials.expired:
        return credentials

    try:
        credentials.refresh(Request())
    except RefreshError as exc:
        logger.error("OAuth token refresh failed for user %s: %s", user.email, exc)
        raise OAuthError(
            "Failed to refresh OAuth token. Re-authentication required."
        ) from exc

    # Persist the new access token and expiry
    user.oauth_access_token = credentials.token
    user.oauth_token_expiry = credentials.expiry
    db.commit()
    logger.info("Refreshed OAuth token for user %s", user.email)

    return credentials
