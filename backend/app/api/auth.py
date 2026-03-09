"""Authentication API routes."""

import logging
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models import User
from app.schemas.auth import LoginResponse, TokenResponse, UserInfo
from app.services.auth_service import create_access_token
from app.services.oauth_service import OAuthError, exchange_code_for_tokens

logger = logging.getLogger(__name__)

router = APIRouter()

_LOGIN_SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly"
    " openid"
    " email"
    " profile"
)


@router.get("/login", response_model=LoginResponse)
def login():
    """Return the Google OAuth2 authorization URL."""
    authorization_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.gmail_client_id}"
        f"&redirect_uri={quote(settings.gmail_redirect_uri, safe='')}"
        "&response_type=code"
        f"&scope={quote(_LOGIN_SCOPES, safe='')}"
        "&access_type=offline"
        "&prompt=consent"
    )
    return LoginResponse(authorization_url=authorization_url)


@router.get("/callback", response_class=RedirectResponse)
def auth_callback(
    code: str = Query(..., description="OAuth authorization code"),
    db: Session = Depends(get_db),
):
    """Exchange an OAuth authorization code for tokens and issue a JWT.

    Exchanges the code with Google for access/refresh tokens, extracts
    the user's email from the id_token, and creates or updates the user.
    Redirects to the frontend with the JWT in the query string.
    """
    frontend_url = settings.allowed_origins[0]  # e.g. http://localhost:3000

    try:
        tokens = exchange_code_for_tokens(code)
    except OAuthError as exc:
        params = urlencode({"error": str(exc)})
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?{params}",
            status_code=status.HTTP_302_FOUND,
        )

    # Look up or create user
    user = db.query(User).filter(User.email == tokens.email).first()
    if user is None:
        user = User(
            email=tokens.email,
            oauth_access_token=tokens.access_token,
            oauth_refresh_token=tokens.refresh_token,
            oauth_token_expiry=tokens.expiry,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created new user: %s", user.email)
    else:
        user.oauth_access_token = tokens.access_token
        user.oauth_refresh_token = tokens.refresh_token
        user.oauth_token_expiry = tokens.expiry
        db.commit()
        db.refresh(user)
        logger.info("Updated existing user: %s", user.email)

    access_token = create_access_token(user.id, user.email)
    params = urlencode({"token": access_token})
    return RedirectResponse(
        url=f"{frontend_url}/auth/callback?{params}",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout():
    """Log out the current user.

    With stateless JWT, logout is handled client-side by discarding
    the token. This endpoint exists for API completeness.
    """
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserInfo)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user's info."""
    return current_user
