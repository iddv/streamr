"""
Feedback endpoints — anonymous or authenticated.
Task 7.4 — Req 24.1–24.4, Design §26
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db
from .auth import get_current_user, AuthenticatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post("/feedback", response_model=schemas.FeedbackResponse, status_code=201)
async def submit_feedback(
    body: schemas.FeedbackCreate,
    db: Session = Depends(get_db),
):
    """
    Submit feedback. JWT is optional — anonymous submissions accepted.
    """
    fb = models.Feedback(
        text=body.text,
        category=body.category,
        node_id=body.node_id,
        user_id=None,  # anonymous by default
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


@router.get("/feedback", response_model=List[schemas.FeedbackResponse])
async def list_feedback(
    category: Optional[str] = None,
    limit: int = 50,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List feedback entries. Requires authentication (admin-only in future).
    """
    query = db.query(models.Feedback).order_by(models.Feedback.created_at.desc())
    if category:
        query = query.filter(models.Feedback.category == category)
    return query.limit(limit).all()
