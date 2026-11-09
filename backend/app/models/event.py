"""
ApplicationEvent model: the audit trail of an application.

Every meaningful change is recorded with a timestamp: answers saved, cleared,
rejected or confirmed, calculated values changing, language changes, status
changes and session resumes. The trail is append-only and is deleted with the
application. It stores answer values (prototype only), see the security notes
in Phase 16.
"""

import enum
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.core.database import Base
from app.models.application import Application  # noqa: F401  (registers the mapper)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventType(str, enum.Enum):
    APPLICATION_CREATED = "application_created"
    SESSION_RESUMED = "session_resumed"
    LANGUAGE_CHANGED = "language_changed"
    FIELD_UPDATED = "field_updated"
    FIELD_CLEARED = "field_cleared"
    FIELD_REJECTED = "field_rejected"
    FIELD_CONFIRMED = "field_confirmed"
    FIELD_CALCULATED = "field_calculated"  # auto-filled by the backend
    FIELD_REMOVED = "field_removed"        # value dropped because the field was hidden
    STATUS_CHANGED = "status_changed"


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    # Auto-increment ID doubles as the order of events
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, native_enum=False, length=30), nullable=False, index=True
    )
    field_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    source: Mapped[str | None] = mapped_column(String(20), nullable=True)  # voice/text/...

    old_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    # Extra context, e.g. validation issues of a rejected answer
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Adds `application.events` (in order)
    application: Mapped["Application"] = relationship(
        "Application",
        backref=backref(
            "events",
            cascade="all, delete-orphan",
            order_by="ApplicationEvent.id",
        ),
    )

    def __repr__(self) -> str:
        return f"<ApplicationEvent id={self.id} type={self.event_type.value}>"