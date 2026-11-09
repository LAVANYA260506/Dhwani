"""
Applicant model: a thin identity and session record for one application.

There are no accounts or logins. The applicant resumes an application with a
session token. Only the SHA-256 hash of the token is stored; the raw token is
returned to the browser once, when the application is created (see
core/security.py). All form answers stay in Application.values. The name and
mobile fields here are display and lookup copies maintained by the
application service, not a second source of truth.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.core.database import Base
from app.models.application import Application  # noqa: F401  (registers the mapper)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class Applicant(Base):
    __tablename__ = "applicants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)

    # One applicant per application
    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # SHA-256 hex digest of the session token (never store the raw token)
    session_token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )

    preferred_language: Mapped[str] = mapped_column(
        String(5), default="en", nullable=False
    )

    # Display/lookup copies, filled in once the applicant provides them
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mobile_number: Mapped[str | None] = mapped_column(String(15), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Adds `application.applicant` automatically; deleting an application
    # deletes its applicant.
    application: Mapped["Application"] = relationship(
        "Application",
        backref=backref("applicant", uselist=False, cascade="all, delete-orphan"),
    )

    def __repr__(self) -> str:
        return f"<Applicant id={self.id} application_id={self.application_id}>"