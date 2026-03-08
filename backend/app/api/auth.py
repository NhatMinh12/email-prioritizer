"""Authentication API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models import User
from app.schemas.auth import LoginResponse, TokenResponse, UserInfo
from app.services.auth_service import create_access_token

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/login", response_model=LoginResponse)
def login():
    """Return the OAuth authorization URL.

    Stub: returns a placeholder URL. Real implementation (Func 3b)
    will build a proper Google OAuth2 authorization URL.
    """
    authorization_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.gmail_client_id}"
        f"&redirect_uri={settings.gmail_redirect_uri}"
        "&response_type=code"
        "&scope=https://www.googleapis.com/auth/gmail.readonly"
        "&access_type=offline"
    )
    return LoginResponse(authorization_url=authorization_url)


@router.get("/callback", response_model=TokenResponse)
def auth_callback(
    code: str = Query(..., description="OAuth authorization code"),
    email: str = Query(..., description="User email (stub param for 3a)"),
    db: Session = Depends(get_db),
):
    """Exchange OAuth code for tokens and issue a JWT.

    Stub: accepts any code, creates/updates user with the provided email,
    and returns a JWT. Real implementation (Func 3b) will exchange the
    code with Google for OAuth tokens.
    """
    # Look up or create user
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email, oauth_token=code)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created new user: %s", user.email)
    else:
        user.oauth_token = code
        db.commit()
        db.refresh(user)
        logger.info("Updated existing user: %s", user.email)

    access_token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=access_token)


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
