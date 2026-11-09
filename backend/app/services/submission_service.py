"""
Submission service: readiness check, review summary and mock submission.

    review = SubmissionService(db).review(application)
    result = SubmissionService(db).submit(application, confirm=True)

- Readiness uses the same validation engine as the form: missing required
  fields, invalid values and broken cross-field rules all block submission.
- Submission needs the applicant's explicit confirmation, is idempotent (a
  second call returns the same reference ID) and goes through the lifecycle
  rules, so nothing can be submitted from the wrong state.
- This is a MOCK: nothing is sent anywhere. The reference ID only proves the
  flow completed.
"""

import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_engine.voice.language_handler import resolve_language
from app.core import lifecycle
from app.core.exceptions import BadRequestError, ConflictError
from app.models import Application, ApplicationEvent, ApplicationStatus, EventType
from app.repositories.application_repository import ApplicationRepository
from app.schemas.submission import (
    ReadinessIssue,
    ReviewItem,
    ReviewRead,
    ReviewSection,
    SubmitResult,
)
from app.services import validation_service
from app.services.agent_service import display_value
from shared.constants import fields as F

# No look-alike characters (0/O, 1/I)
_REF_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

TEXT = {
    "confirm_needed": {
        "en": "Please confirm that the information is correct before submitting.",
        "kn": "ಸಲ್ಲಿಸುವ ಮೊದಲು ಮಾಹಿತಿ ಸರಿಯಾಗಿದೆ ಎಂದು ದಯವಿಟ್ಟು ಖಚಿತಪಡಿಸಿ.",
    },
    "not_ready": {
        "en": "The application is not complete yet. Please fix the items listed.",
        "kn": "ಅರ್ಜಿ ಇನ್ನೂ ಪೂರ್ಣವಾಗಿಲ್ಲ. ಪಟ್ಟಿ ಮಾಡಿದ ಅಂಶಗಳನ್ನು ಸರಿಪಡಿಸಿ.",
    },
    "missing": {"en": "This required information is missing.", "kn": "ಈ ಅಗತ್ಯ ಮಾಹಿತಿ ಕಾಣೆಯಾಗಿದೆ."},
}


def _t(key: str, lang: str) -> str:
    return TEXT[key][lang]


class SubmissionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ApplicationRepository(db)

    # -----------------------------------------------------------------
    # Review
    # -----------------------------------------------------------------
    def review(self, application: Application) -> ReviewRead:
        lang = resolve_language(application.language)
        values = dict(application.values)
        schema = F.load_schema()

        section_of: dict[str, tuple[str, str]] = {}
        for section in schema["sections"]:
            for field in section["fields"]:
                section_of[field["id"]] = (section["id"], section["title"][lang])

        missing, field_issues, violations = validation_service.validate_application(values, lang)

        issues: list[ReadinessIssue] = []
        for field_id in missing:
            section_id, section_title = section_of.get(field_id, (None, None))
            issues.append(ReadinessIssue(
                kind="missing", field_id=field_id, label=F.get_label(field_id, lang),
                section_id=section_id, section_title=section_title, message=_t("missing", lang),
            ))
        for field_id, field_problems in field_issues.items():
            section_id, section_title = section_of.get(field_id, (None, None))
            first = field_problems[0]
            issues.append(ReadinessIssue(
                kind="invalid", field_id=field_id, label=F.get_label(field_id, lang),
                section_id=section_id, section_title=section_title,
                message=f"{first.message} {first.hint or ''}".strip(),
            ))
        for violation in violations:
            first_field = violation.fields[0]
            section_id, section_title = section_of.get(first_field, (None, None))
            issues.append(ReadinessIssue(
                kind="cross_field", field_id=first_field, label=F.get_label(first_field, lang),
                section_id=section_id, section_title=section_title, message=violation.message,
            ))

        # Pending marks-card discrepancies (Phase 7) will be added here later.

        sections: list[ReviewSection] = []
        for section in schema["sections"]:
            items: list[ReviewItem] = []
            for field in section["fields"]:
                field_id = field["id"]
                if not F.is_visible(field_id, values) or not F.is_answered(field_id, values.get(field_id)):
                    continue
                value = values[field_id]
                items.append(ReviewItem(
                    field_id=field_id,
                    label=F.get_label(field_id, lang),
                    display=display_value(field_id, value, lang),
                    value=value,
                    source=application.field_sources.get(field_id),
                    confirmed=field_id in application.confirmed_fields,
                ))
            if items:
                sections.append(ReviewSection(id=section["id"], title=section["title"][lang], items=items))

        ready = not issues
        submitted = application.status == ApplicationStatus.SUBMITTED
        return ReviewRead(
            status=application.status.value,
            language=lang,
            ready=ready,
            can_submit=ready and not submitted,
            submitted=submitted,
            reference_id=application.reference_id,
            submitted_at=application.submitted_at,
            issues=issues,
            sections=sections,
        )

    # -----------------------------------------------------------------
    # Mock submission
    # -----------------------------------------------------------------
    def submit(self, application: Application, confirm: bool) -> SubmitResult:
        lang = resolve_language(application.language)

        # Idempotent: submitting twice returns the same reference ID
        if application.status == ApplicationStatus.SUBMITTED and application.reference_id:
            return SubmitResult(
                reference_id=application.reference_id,
                submitted_at=application.submitted_at or datetime.now(timezone.utc),
                status=application.status.value,
                already_submitted=True,
            )

        if not confirm:
            raise BadRequestError(_t("confirm_needed", lang))

        review = self.review(application)
        if not review.ready:
            raise ConflictError(
                _t("not_ready", lang),
                details=[issue.model_dump() for issue in review.issues],
            )

        # A complete application may still be marked in_progress (for example
        # data saved before the readiness rules existed): move it along first
        if application.status == ApplicationStatus.IN_PROGRESS:
            self._move(application, ApplicationStatus.READY_FOR_REVIEW)

        now = datetime.now(timezone.utc)
        reference_id = self._new_reference_id(now)
        self._move(application, ApplicationStatus.SUBMITTED, details={"reference_id": reference_id})
        application.reference_id = reference_id
        application.submitted_at = now
        self.repo.save(application)

        return SubmitResult(
            reference_id=reference_id, submitted_at=now, status=application.status.value
        )

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    def _move(
        self, application: Application, target: ApplicationStatus, details: dict | None = None
    ) -> None:
        lifecycle.assert_transition(application.status, target)
        self.repo.record_event(
            ApplicationEvent(
                application_id=application.id,
                event_type=EventType.STATUS_CHANGED,
                old_value=application.status.value,
                new_value=target.value,
                details=details,
            )
        )
        application.status = target

    def _new_reference_id(self, now: datetime) -> str:
        """EV-EDU-YYYYMMDD-XXXXXX, unique."""
        for _ in range(10):
            suffix = "".join(secrets.choice(_REF_ALPHABET) for _ in range(6))
            candidate = f"EV-EDU-{now:%Y%m%d}-{suffix}"
            taken = self.db.execute(
                select(Application.id).where(Application.reference_id == candidate)
            ).first()
            if taken is None:
                return candidate
        raise ConflictError("Could not generate a reference ID. Please try again.")