"""
Validation endpoints (all under /api). Both need the session token.

    POST /validation/field         check one value without saving it
    GET  /validation/application   check the whole application
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_application
from app.models import Application
from app.schemas.validation import (
    ApplicationValidationResult,
    CrossFieldIssue,
    ValidationCheckRequest,
    ValidationCheckResult,
)
from app.services import validation_service

router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("/field", response_model=ValidationCheckResult)
def check_field(
    payload: ValidationCheckRequest,
    application: Application = Depends(get_current_application),
):
    values = dict(application.values)
    stored, issues = validation_service.validate_field(
        payload.field_id, payload.value, values, application.language
    )
    if not issues:
        issues = validation_service.check_cross_rules(
            {**values, payload.field_id: stored},
            application.language,
            changed_field=payload.field_id,
        )
    return ValidationCheckResult(
        field_id=payload.field_id,
        valid=not issues,
        value=None if issues else stored,
        issues=issues,
    )


@router.get("/application", response_model=ApplicationValidationResult)
def check_application(application: Application = Depends(get_current_application)):
    missing, field_issues, violations = validation_service.validate_application(
        dict(application.values), application.language
    )
    return ApplicationValidationResult(
        valid=not missing and not field_issues and not violations,
        missing_required=missing,
        field_issues=field_issues,
        cross_field_issues=[
            CrossFieldIssue(rule_id=v.rule_id, fields=v.fields, message=v.message)
            for v in violations
        ],
    )