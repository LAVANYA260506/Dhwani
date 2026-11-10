"""
Database access for applications. Services use this instead of writing
queries themselves, so all SQL lives in one place.
"""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Applicant, Application, ApplicationEvent, EventType


class ApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, application_id: str) -> Application | None:
        return self.db.get(Application, application_id)

    def get_by_token_hash(self, token_hash: str) -> Application | None:
        """Find the application whose applicant holds this session token."""
        statement = (
            select(Application)
            .join(Applicant, Applicant.application_id == Application.id)
            .where(Applicant.session_token_hash == token_hash)
        )
        return self.db.execute(statement).scalar_one_or_none()

    def add(self, application: Application, applicant: Applicant) -> Application:
        """Insert a new application together with its applicant."""
        self.db.add(application)
        self.db.flush()  # assigns application.id
        applicant.application_id = application.id
        self.db.add(applicant)
        self.db.commit()
        self.db.refresh(application)
        return application

    def save(self, application: Application) -> Application:
        """Commit the application and any events recorded since the last save."""
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        return application

    def delete(self, application: Application) -> None:
        """Delete one application with everything attached to it."""
        self.db.delete(application)
        self.db.commit()

    def delete_stale(self, older_than: datetime) -> int:
        """Delete applications not touched since `older_than`. The database
        removes their answers, messages and events through the foreign keys."""
        result = self.db.execute(delete(Application).where(Application.updated_at < older_than))
        self.db.commit()
        return result.rowcount or 0
    
    # -----------------------------------------------------------------
    # Event trail
    # -----------------------------------------------------------------
    def record_event(self, event: ApplicationEvent) -> None:
        """Queue an event. It is committed together with the next save(), so a
        change and its event are stored atomically."""
        self.db.add(event)

    def list_events(
        self, application_id: str, limit: int = 50, after_id: int | None = None
    ) -> list[ApplicationEvent]:
        """Chronological events. Without `after_id`, the latest `limit` events;
        with it, the next `limit` events after that ID."""
        statement = select(ApplicationEvent).where(
            ApplicationEvent.application_id == application_id
        )
        if after_id is not None:
            statement = statement.where(ApplicationEvent.id > after_id).order_by(
                ApplicationEvent.id.asc()
            )
            return list(self.db.execute(statement.limit(limit)).scalars())
        statement = statement.order_by(ApplicationEvent.id.desc()).limit(limit)
        return list(reversed(list(self.db.execute(statement).scalars())))

    def latest_field_attempts(self, application_id: str) -> dict[str, ApplicationEvent]:
        """The most recent update/clear/reject event for each field."""
        statement = (
            select(ApplicationEvent)
            .where(
                ApplicationEvent.application_id == application_id,
                ApplicationEvent.event_type.in_(
                    [
                        EventType.FIELD_UPDATED,
                        EventType.FIELD_CLEARED,
                        EventType.FIELD_REJECTED,
                    ]
                ),
            )
            .order_by(ApplicationEvent.id.asc())
        )
        latest: dict[str, ApplicationEvent] = {}
        for event in self.db.execute(statement).scalars():
            if event.field_id:
                latest[event.field_id] = event
        return latest