"""Email API routes."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import (
    get_cache_service,
    get_claude_service,
    get_current_user,
    get_gmail_service,
)
from app.db.database import get_db
from app.models import Classification, Email, User, UserPreference
from app.models.base import PriorityLevel
from app.schemas.classification import ClassificationFeedback, ClassificationResponse
from app.schemas.email import EmailCreate, EmailListResponse, EmailResponse
from app.services.cache_service import CacheService
from app.services.classifier import EmailClassifier
from app.services.claude_service import ClaudeService
from app.services.gmail_service import GmailService
from app.services.oauth_service import OAuthError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=EmailListResponse)
def list_emails(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    priority: Optional[PriorityLevel] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get paginated list of emails for the current user.

    Optionally filter by priority level.
    """
    query = (
        db.query(Email)
        .options(joinedload(Email.classification))
        .filter(Email.user_id == current_user.id)
    )

    if priority is not None:
        query = query.join(Email.classification).filter(
            Classification.priority == priority
        )

    total = query.count()
    emails = (
        query.order_by(Email.received_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return EmailListResponse(
        emails=[EmailResponse.model_validate(e) for e in emails],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{email_id}", response_model=EmailResponse)
def get_email(
    email_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single email with its classification.

    Returns 404 if the email doesn't exist or belongs to another user
    (to avoid leaking existence info).
    """
    email = (
        db.query(Email)
        .options(joinedload(Email.classification))
        .filter(Email.id == email_id, Email.user_id == current_user.id)
        .first()
    )
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    return EmailResponse.model_validate(email)


@router.post("/sync", status_code=status.HTTP_200_OK)
def sync_emails(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    gmail_service: GmailService = Depends(get_gmail_service),
):
    """Trigger email sync from Gmail.

    Fetches new emails and stores them in the database,
    deduplicating by gmail_id.
    """
    try:
        raw_emails = gmail_service.fetch_emails(current_user.id)
    except OAuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gmail re-authentication required",
        )
    except Exception as exc:
        logger.error("Gmail sync failed for user %s: %s", current_user.email, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch emails from Gmail",
        )

    new_count = 0
    for raw in raw_emails:
        email_data = EmailCreate(**raw)
        existing = (
            db.query(Email)
            .filter(
                Email.user_id == current_user.id,
                Email.gmail_id == email_data.gmail_id,
            )
            .first()
        )
        if existing is None:
            email = Email(
                user_id=current_user.id,
                gmail_id=email_data.gmail_id,
                sender=email_data.sender,
                subject=email_data.subject,
                body_preview=email_data.body_preview,
                received_at=email_data.received_at,
                has_attachments=email_data.has_attachments,
                thread_length=email_data.thread_length,
            )
            db.add(email)
            new_count += 1

    db.commit()
    logger.info(
        "Synced %d new emails for user %s", new_count, current_user.email
    )
    return {"synced": new_count}


@router.post("/classify", status_code=status.HTTP_200_OK)
def classify_emails(
    email_ids: Optional[list[uuid.UUID]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    cache_service: CacheService = Depends(get_cache_service),
    claude_service: ClaudeService = Depends(get_claude_service),
):
    """Trigger classification for unclassified emails.

    If email_ids is provided, only classify those emails.
    Otherwise, classify all unclassified emails for the current user.

    For batches > 10, classification runs in the background
    and returns 202 Accepted.
    """
    query = (
        db.query(Email)
        .outerjoin(Email.classification)
        .filter(
            Email.user_id == current_user.id,
            Classification.id.is_(None),
        )
    )

    if email_ids is not None:
        query = query.filter(Email.id.in_(email_ids))

    emails = query.all()

    if not emails:
        return {"classified": 0, "message": "No unclassified emails found"}

    preferences = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == current_user.id)
        .first()
    )

    classifier = EmailClassifier(
        db_session=db,
        claude_service=claude_service,
        cache_service=cache_service,
    )

    if len(emails) > 10:
        # Capture IDs — the request's DB session will be closed by the time
        # the background task runs, so we must re-query in a fresh session.
        email_ids_to_classify = [e.id for e in emails]
        user_id = current_user.id
        background_tasks.add_task(
            _run_classification,
            email_ids_to_classify,
            user_id,
            claude_service,
            cache_service,
        )
        return {
            "classified": 0,
            "message": f"Classification of {len(emails)} emails started in background",
            "status": "accepted",
        }

    classifications = classifier.classify_emails(emails, preferences)
    db.commit()

    return {
        "classified": len(classifications),
        "message": f"Successfully classified {len(classifications)} emails",
    }


def _run_classification(
    email_ids: list[uuid.UUID],
    user_id: uuid.UUID,
    claude_service: ClaudeService,
    cache_service: CacheService,
) -> None:
    """Background task for classifying large batches.

    Creates its own DB session since the request session is closed
    by the time background tasks execute.
    """
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        emails = (
            db.query(Email)
            .outerjoin(Email.classification)
            .filter(
                Email.id.in_(email_ids),
                Classification.id.is_(None),
            )
            .all()
        )

        if not emails:
            logger.info("Background classification: no unclassified emails remaining")
            return

        preferences = (
            db.query(UserPreference)
            .filter(UserPreference.user_id == user_id)
            .first()
        )

        classifier = EmailClassifier(
            db_session=db,
            claude_service=claude_service,
            cache_service=cache_service,
        )
        classifier.classify_emails(emails, preferences)
        db.commit()
        logger.info("Background classification completed: %d emails", len(emails))
    except Exception as exc:
        logger.error("Background classification failed: %s", exc)
        db.rollback()
    finally:
        db.close()


@router.post("/{email_id}/feedback", response_model=ClassificationResponse)
def submit_feedback(
    email_id: uuid.UUID,
    feedback: ClassificationFeedback,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit user feedback on an email's classification."""
    email = (
        db.query(Email)
        .filter(Email.id == email_id, Email.user_id == current_user.id)
        .first()
    )
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )

    classification = (
        db.query(Classification)
        .filter(Classification.email_id == email_id)
        .first()
    )
    if classification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No classification found for this email",
        )

    classification.feedback = feedback.feedback
    db.commit()
    db.refresh(classification)
    logger.info(
        "Feedback '%s' submitted for email %s", feedback.feedback, email_id
    )
    return ClassificationResponse.model_validate(classification)
