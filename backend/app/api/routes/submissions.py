"""
Review and mock-submission endpoints (all under /api). Both need the session token.

    GET  /submission/review   readiness check + readable summary of every answer
    POST /submission/submit   mock submission; body {"confirm": true}; returns a reference ID
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_application
from app.core.database import get_db
from app.models import Application
from app.schemas.submission import ReviewRead, SubmitRequest, SubmitResult
from app.services.submission_service import SubmissionService

router = APIRouter(prefix="/submission", tags=["submission"])


@router.get("/review", response_model=ReviewRead)
def review(
    application: Application = Depends(get_current_application),
    db: Session = Depends(get_db),
):
    return SubmissionService(db).review(application)


@router.post("/submit", response_model=SubmitResult)
def submit(
    payload: SubmitRequest,
    application: Application = Depends(get_current_application),
    db: Session = Depends(get_db),
):
    return SubmissionService(db).submit(application, payload.confirm)