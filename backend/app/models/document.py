"""
Document model: an uploaded document (the marks card in the MVP).

An application can have several documents, for example when the applicant
replaces a blurry upload. The most recent successfully extracted document is
flagged `is_current` and is the one compared with the form.

The file itself lives in the upload folder under `stored_filename` (a
generated name, never the user's file name). Only that name is stored here,
so the folder can move without changing the database.
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.core.database import Base
from app.models.application import Application  # noqa: F401  (registers the mapper)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class DocumentType(str, enum.Enum):
    MARKS_CARD = "marks_card"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"      # saved, extraction not started
    PROCESSING = "processing"  # extraction in progress
    EXTRACTED = "extracted"    # data extracted successfully
    FAILED = "failed"          # extraction failed, see error_message


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)

    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    doc_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, native_enum=False, length=20),
        default=DocumentType.MARKS_CARD,
        nullable=False,
    )

    # File details
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Extraction
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False, length=20),
        default=DocumentStatus.UPLOADED,
        nullable=False,
        index=True,
    )
    # Normalised values, keyed by form field ID, e.g. {"register_number": "...",
    # "marks_obtained": 512, "max_marks": 600}. Only fields found on the card.
    extracted_data: Mapped[dict[str, Any] | None] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True
    )
    # Latest comparison with the form: matches, mismatches and fields not found
    comparison_result: Mapped[dict[str, Any] | None] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # True for the document currently used for comparison
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Adds `application.documents` (oldest first). The database removes the rows
    # when an application is deleted; the document service must also delete the
    # files from the upload folder.
    application: Mapped["Application"] = relationship(
        "Application",
        backref=backref(
            "documents",
            cascade="all, delete-orphan",
            order_by="Document.created_at",
        ),
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} status={self.status.value}>"