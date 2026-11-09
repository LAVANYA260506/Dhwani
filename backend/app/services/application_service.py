"""
Application service: the business logic for one loan application.

Routes (and later the agent's tools) call this service; it is the only place
that changes application state. Voice and typed answers share one save path
(`update_field`); the only difference is the `source` recorded with the value.

Every change is written to the event trail in the same commit as the change
itself. Field checks live in `_validate`, which holds basic type and choice
checks for now. Phase 6 replaces its body with the full validation engine.
"""

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core import lifecycle
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationFailedError
from app.core.security import generate_session_token, hash_token
from app.models import (
    Applicant,
    Application,
    ApplicationEvent,
    ApplicationStatus,
    EventType,
)
from app.repositories.application_repository import ApplicationRepository
from app.schemas.application import (
    ApplicationCreate,
    ApplicationCreated,
    ApplicationRead,
    FieldConfirm,
    FieldIssue,
    FieldStatus,
    FieldUpdate,
    FieldUpdateResult,
    InvalidField,
    ProgressSummary,
    SectionProgress,
)
from app.services import validation_service
from app.schemas.events import EventList, EventRead
from shared.constants import fields as F
from shared.constants.languages import normalize_digits

NUMERIC_TYPES = {"number", "currency", "year", "percentage"}
_NUMBER_PATTERN = re.compile(r"^-?\d+(\.\d+)?$")
_TRUE_WORDS = {"true", "yes", "y", "1"}
_FALSE_WORDS = {"false", "no", "n", "0"}

TUITION_PARTS = [
    "tuition_fee_total",
    "hostel_fee_total",
    "books_equipment_cost",
    "travel_cost",
    "other_expenses",
]


def _number_or_none(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


class ApplicationService:
    def __init__(self, db: Session):
        self.repo = ApplicationRepository(db)

    # -----------------------------------------------------------------
    # Create, authenticate and resume
    # -----------------------------------------------------------------
    def create_application(self, payload: ApplicationCreate) -> ApplicationCreated:
        if not payload.consent_given:
            raise ValidationFailedError(
                "Consent is required to start an application."
            )

        raw_token, token_hash = generate_session_token()
        now = datetime.now(timezone.utc)

        application = Application(
            status=ApplicationStatus.IN_PROGRESS,
            language=payload.language,
            values={},
            confirmed_fields=[],
            field_sources={},
            consent_given=True,
            consent_given_at=now,
        )
        applicant = Applicant(
            session_token_hash=token_hash,
            preferred_language=payload.language,
        )
        application.current_field = F.next_field_to_ask({})
        self.repo.add(application, applicant)

        self._log(
            application,
            EventType.APPLICATION_CREATED,
            details={"language": payload.language},
        )
        self.repo.save(application)

        return ApplicationCreated(
            application_id=application.id,
            session_token=raw_token,
            status=application.status.value,
            language=application.language,
        )

    def authenticate(self, raw_token: str) -> Application:
        application = self.repo.get_by_token_hash(hash_token(raw_token))
        if application is None:
            raise UnauthorizedError("This session is not valid. Please start again.")
        application.applicant.last_active_at = datetime.now(timezone.utc)
        return self.repo.save(application)

    def resume(self, application: Application) -> ApplicationRead:
        """Restore an application from its session token: full state, field
        status and the field to ask about next."""
        self._log(application, EventType.SESSION_RESUMED)
        self.repo.save(application)
        return self.get_state(application)

    # -----------------------------------------------------------------
    # Read
    # -----------------------------------------------------------------
    def get_state(self, application: Application) -> ApplicationRead:
        return ApplicationRead(
            id=application.id,
            status=application.status.value,
            language=application.language,
            values=dict(application.values),
            confirmed_fields=list(application.confirmed_fields),
            field_sources=dict(application.field_sources),
            current_field=application.current_field,
            consent_given=application.consent_given,
            reference_id=application.reference_id,
            created_at=application.created_at,
            updated_at=application.updated_at,
            progress=self.build_progress(application.values),
            field_status=self.build_field_status(application),
        )

    @staticmethod
    def build_progress(values: dict[str, Any]) -> ProgressSummary:
        required = F.required_field_ids(values)
        answered = sum(1 for i in required if F.is_answered(i, values.get(i)))
        total = len(required)

        # Complete only when every required field, including calculated
        # ones, has a value
        missing = [
            i
            for i in F.required_field_ids(values, include_calculated=True)
            if not F.is_answered(i, values.get(i))
        ]
        return ProgressSummary(
            answered_required=answered,
            total_required=total,
            percent=round(answered / total * 100, 1) if total else 0.0,
            complete=not missing,
            sections=[
                SectionProgress(section_id=section_id, **counts)
                for section_id, counts in F.section_progress(values).items()
            ],
        )

    def build_field_status(self, application: Application) -> FieldStatus:
        """Split the required, visible fields into completed, pending and
        invalid.

        - completed: has an accepted value
        - invalid:   no value, and the latest attempt was rejected
        - pending:   no value and nothing rejected (not asked yet, or cleared)
        """
        values = application.values
        attempts = self.repo.latest_field_attempts(application.id)

        completed: list[str] = []
        pending: list[str] = []
        invalid: list[InvalidField] = []

        for field_id in F.required_field_ids(values, include_calculated=True):
            if F.is_answered(field_id, values.get(field_id)):
                completed.append(field_id)
                continue

            attempt = attempts.get(field_id)
            if attempt is not None and attempt.event_type == EventType.FIELD_REJECTED:
                issues = (attempt.details or {}).get("issues") or []
                first = issues[0] if issues else {}
                invalid.append(
                    InvalidField(
                        field_id=field_id,
                        code=first.get("code", "invalid_value"),
                        message=first.get("message", "This value is not valid."),
                        hint=first.get("hint"),
                    )
                )
            else:
                pending.append(field_id)

        return FieldStatus(completed=completed, pending=pending, invalid=invalid)

    def list_events(
        self, application: Application, limit: int = 50, after_id: int | None = None
    ) -> EventList:
        events = self.repo.list_events(application.id, limit=limit, after_id=after_id)
        return EventList(events=[EventRead.model_validate(e) for e in events])

    # -----------------------------------------------------------------
    # Language
    # -----------------------------------------------------------------
    def update_language(self, application: Application, language: str) -> ApplicationRead:
        self._ensure_editable(application)
        if application.language != language:
            self._log(
                application,
                EventType.LANGUAGE_CHANGED,
                old=application.language,
                new=language,
            )
        application.language = language
        application.applicant.preferred_language = language
        self.repo.save(application)
        return self.get_state(application)

    # -----------------------------------------------------------------
    # Save an answer (the single path for voice and typed input)
    # -----------------------------------------------------------------
    def update_field(self, application: Application, payload: FieldUpdate) -> FieldUpdateResult:
        self._ensure_editable(application)
        field_id = payload.field_id

        if not F.field_exists(field_id):
            return self._rejected(
                application, field_id,
                FieldIssue(code="unknown_field", message=f"'{field_id}' is not a field in this form."),
            )

        field = F.get_field(field_id)
        if field.get("calculated"):
            return self._rejected(
                application, field_id,
                FieldIssue(
                    code="calculated_field",
                    message="This value is worked out automatically from other answers.",
                ),
            )
        if not F.is_visible(field_id, application.values):
            return self._rejected(
                application, field_id,
                FieldIssue(
                    code="field_not_applicable",
                    message="This field does not apply based on your earlier answers.",
                ),
            )

        old_value = application.values.get(field_id)

        # Empty value clears the field
        if _is_blank(payload.value):
            if field_id in application.values:
                self._log(application, EventType.FIELD_CLEARED, field_id=field_id, old=old_value)
            self._remove_value(application, field_id)
            stored_value = None
        else:
            stored_value, issues = self._validate(field_id, payload.value, application.values,application.language)
            if issues:
                return self._rejected(
                    application, field_id, *issues,
                    record=True, attempted=payload.value, source=payload.source,
                )
            application.values[field_id] = stored_value
            application.field_sources[field_id] = payload.source
            if field_id in application.confirmed_fields:
                application.confirmed_fields.remove(field_id)
            self._log(
                application,
                EventType.FIELD_UPDATED,
                field_id=field_id,
                source=payload.source,
                old=old_value,
                new=stored_value,
            )

        self._prune_hidden(application)
        auto_filled = self._recalculate(application)
        self._refresh_status(application)
        self.repo.save(application)

        return FieldUpdateResult(
            field_id=field_id,
            accepted=True,
            value=stored_value,
            auto_filled=auto_filled,
            next_field=application.current_field,
            progress=self.build_progress(application.values),
            field_status=self.build_field_status(application),
        )

    # -----------------------------------------------------------------
    # Confirm a field (calculated values, resolved conflicts)
    # -----------------------------------------------------------------
    def confirm_field(self, application: Application, payload: FieldConfirm) -> FieldUpdateResult:
        self._ensure_editable(application)
        field_id = payload.field_id

        if not F.field_exists(field_id):
            return self._rejected(
                application, field_id,
                FieldIssue(code="unknown_field", message=f"'{field_id}' is not a field in this form."),
            )

        # A value means "use this one": save it first
        if payload.value is not None:
            result = self.update_field(
                application,
                FieldUpdate(field_id=field_id, value=payload.value, source="text"),
            )
            if not result.accepted:
                return result

        if not F.is_visible(field_id, application.values) or not F.is_answered(
            field_id, application.values.get(field_id)
        ):
            return self._rejected(
                application, field_id,
                FieldIssue(code="nothing_to_confirm", message="There is no value to confirm yet."),
            )

        if field_id not in application.confirmed_fields:
            application.confirmed_fields.append(field_id)
            self._log(
                application,
                EventType.FIELD_CONFIRMED,
                field_id=field_id,
                new=application.values.get(field_id),
            )
        self.repo.save(application)

        return FieldUpdateResult(
            field_id=field_id,
            accepted=True,
            value=application.values.get(field_id),
            next_field=application.current_field,
            progress=self.build_progress(application.values),
            field_status=self.build_field_status(application),
        )

        # -----------------------------------------------------------------
    # Validation (delegates to the validation engine)
    # -----------------------------------------------------------------
    def _validate(
        self, field_id: str, value: Any, values: dict[str, Any], language: str = "en"
    ) -> tuple[Any, list[FieldIssue]]:
        """Return (cleaned_value, issues). Issues empty means accepted.
        Checks the field itself, then the cross-field rules it takes part in."""
        stored, issues = validation_service.validate_field(
            field_id, value, values, language
        )
        if issues:
            return None, issues

        issues = validation_service.check_cross_rules(
            {**values, field_id: stored}, language, changed_field=field_id
        )
        if issues:
            return None, issues
        return stored, []

    # -----------------------------------------------------------------
    # State helpers
    # -----------------------------------------------------------------
    @staticmethod
    def _ensure_editable(application: Application) -> None:
        if not lifecycle.is_editable(application.status):
            raise ConflictError("This application has already been submitted.")

    @staticmethod
    def _remove_value(application: Application, field_id: str) -> None:
        application.values.pop(field_id, None)
        application.field_sources.pop(field_id, None)
        if field_id in application.confirmed_fields:
            application.confirmed_fields.remove(field_id)

    def _prune_hidden(self, application: Application) -> None:
        """Drop values of fields that are no longer shown, for example the
        country name after switching from Abroad to India."""
        visible = set(F.visible_field_ids(application.values))
        for field_id in list(application.values.keys()):
            if field_id not in visible:
                self._log(
                    application,
                    EventType.FIELD_REMOVED,
                    field_id=field_id,
                    old=application.values.get(field_id),
                    details={"reason": "field_hidden"},
                )
                self._remove_value(application, field_id)

    def _recalculate(self, application: Application) -> dict[str, Any]:
        """Update calculated fields. Returns the ones that changed."""
        values = application.values
        changed: dict[str, Any] = {}

        # percentage = marks obtained / maximum marks * 100
        marks = _number_or_none(values.get("marks_obtained"))
        maximum = _number_or_none(values.get("max_marks"))
        percentage = (
            round(marks / maximum * 100, 2)
            if marks is not None and maximum and marks <= maximum
            else None
        )
        changed.update(self._set_calculated(application, "percentage", percentage))

        # total course cost = sum of the cost parts (missing parts count as 0),
        # shown once tuition and hostel costs are both known
        parts = [_number_or_none(values.get(p)) for p in TUITION_PARTS]
        total = None
        if parts[0] is not None and parts[1] is not None:
            total = sum(p for p in parts if p is not None)
            if isinstance(total, float) and total.is_integer():
                total = int(total)
        changed.update(self._set_calculated(application, "total_course_cost", total))

        return changed

    def _set_calculated(
        self, application: Application, field_id: str, new_value: Any
    ) -> dict[str, Any]:
        old_value = application.values.get(field_id)
        if new_value is None:
            if field_id in application.values:
                self._log(
                    application, EventType.FIELD_CALCULATED,
                    field_id=field_id, source="calculated", old=old_value, new=None,
                )
                self._remove_value(application, field_id)
                return {field_id: None}
            return {}
        if old_value != new_value:
            application.values[field_id] = new_value
            application.field_sources[field_id] = "calculated"
            if field_id in application.confirmed_fields:
                application.confirmed_fields.remove(field_id)
            self._log(
                application, EventType.FIELD_CALCULATED,
                field_id=field_id, source="calculated", old=old_value, new=new_value,
            )
            return {field_id: new_value}
        return {}

    def _refresh_status(self, application: Application) -> None:
        """Recompute the next field and move the status along the lifecycle."""
        application.current_field = F.next_field_to_ask(application.values)
        if application.status == ApplicationStatus.SUBMITTED:
            return

        progress = self.build_progress(application.values)
        target = (
            ApplicationStatus.READY_FOR_REVIEW
            if progress.complete
            else ApplicationStatus.IN_PROGRESS
        )
        if application.status != target:
            self._change_status(application, target)

    def _change_status(self, application: Application, target: ApplicationStatus) -> None:
        lifecycle.assert_transition(application.status, target)
        self._log(
            application,
            EventType.STATUS_CHANGED,
            old=application.status.value,
            new=target.value,
        )
        application.status = target

    def _log(
        self,
        application: Application,
        event_type: EventType,
        *,
        field_id: str | None = None,
        source: str | None = None,
        old: Any = None,
        new: Any = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Queue an event; it is committed with the next repo.save()."""
        self.repo.record_event(
            ApplicationEvent(
                application_id=application.id,
                event_type=event_type,
                field_id=field_id,
                source=source,
                old_value=old,
                new_value=new,
                details=details,
            )
        )

    def _rejected(
        self,
        application: Application,
        field_id: str,
        *issues: FieldIssue,
        record: bool = False,
        attempted: Any = None,
        source: str | None = None,
    ) -> FieldUpdateResult:
        """Build a 'not accepted' result. With record=True (validation
        failures) the attempt is added to the event trail, which is what marks
        the field as invalid in the field status."""
        if record:
            self._log(
                application,
                EventType.FIELD_REJECTED,
                field_id=field_id,
                source=source,
                details={
                    "issues": [issue.model_dump() for issue in issues],
                    "attempted": attempted,
                },
            )
            self.repo.save(application)

        return FieldUpdateResult(
            field_id=field_id,
            accepted=False,
            issues=list(issues),
            next_field=application.current_field,
            progress=self.build_progress(application.values),
            field_status=self.build_field_status(application),
        )