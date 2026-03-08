"""User preferences API routes."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models import User, UserPreference
from app.schemas.user import UserPreferenceResponse, UserPreferenceUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=UserPreferenceResponse)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's preferences.

    Creates default preferences if none exist.
    """
    pref = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()

    if pref is None:
        pref = UserPreference(
            user_id=current_user.id,
            important_senders=[],
            important_keywords=[],
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
        logger.info("Created default preferences for user %s", current_user.email)

    return pref


@router.put("", response_model=UserPreferenceResponse)
def update_preferences(
    updates: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's preferences.

    Only provided fields are updated (partial update).
    Creates preferences if they don't exist yet.
    """
    pref = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()

    if pref is None:
        pref = UserPreference(
            user_id=current_user.id,
            important_senders=[],
            important_keywords=[],
        )
        db.add(pref)
        db.flush()

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pref, field, value)

    db.commit()
    db.refresh(pref)
    logger.info("Updated preferences for user %s", current_user.email)
    return pref
