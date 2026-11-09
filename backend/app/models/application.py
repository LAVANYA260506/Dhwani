"""
Application model: one education-loan application.

The 75 form answers are stored together in `values` (JSON, keyed by the field
IDs from shared/schemas/application_schema.json). Adding or changing a field
in the schema therefore needs no database migration.
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, String
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class ApplicationStatus(str, enum.Enum):
    DRAFT = "draft"                        # created, language and consent pending
    IN_PROGRESS = "in_progress"            # applicant is filling the form
    READY_FOR_REVIEW = "ready_for_review"  # required fields complete, review stage
    SUBMITTED = "submitted"                # mock submission done, reference ID issued


class FieldSource(str, enum.Enum):
    """Where a field value came from. Stored in `field_sources`."""
    VOICE = "voice"
    TEXT = "text"
    DOCUMENT = "document"
    CALCULATED = "calculated"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)

    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, native_enum=False, length=20),
        default=ApplicationStatus.DRAFT,
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(5), default="en", nullable=False)

    # Form answers: {"full_name": "...", "study_country": "abroad", ...}
    values: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON), default=dict, nullable=False
    )
    # Field IDs the applicant has explicitly confirmed (conflicts, calculated fields)
    confirmed_fields: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSON), default=list, nullable=False
    )
    # Source of each value: {"full_name": "voice", "percentage": "calculated"}
    field_sources: Mapped[dict[str, str]] = mapped_column(
        MutableDict.as_mutable(JSON), default=dict, nullable=False
    )

    # The field the assistant is currently asking about (for resuming)
    current_field: Mapped[str | None] = mapped_column(String(80), nullable=True)

    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Set on mock submission
    reference_id: Mapped[str | None] = mapped_column(
        String(30), unique=True, nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Application id={self.id} status={self.status.value}>"