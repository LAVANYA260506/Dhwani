"""
Shared FastAPI dependencies.

`get_current_application` reads the session token from the
`Authorization: Bearer <token>` header and returns that applicant's
application, so a request can only ever touch its own application.
"""

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import parse_bearer_token
from app.models import Application
from app.services.application_service import ApplicationService


def get_application_service(db: Session = Depends(get_db)) -> ApplicationService:
    return ApplicationService(db)


def get_current_application(
    authorization: str | None = Header(default=None),
    service: ApplicationService = Depends(get_application_service),
) -> Application:
    token = parse_bearer_token(authorization)
    if token is None:
        raise UnauthorizedError("A session token is required.")
    return service.authenticate(token)