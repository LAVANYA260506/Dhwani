"""Pydantic schemas for the validation endpoints."""

from pydantic import BaseModel, Field

from app.schemas.application import FIELD_ID_PATTERN, FieldIssue, FieldValue


class ValidationCheckRequest(BaseModel):
    field_id: str = Field(..., pattern=FIELD_ID_PATTERN, max_length=80)
    value: FieldValue


class ValidationCheckResult(BaseModel):
    """Result of checking one value. Nothing is saved."""

    field_id: str
    valid: bool
    value: FieldValue = Field(None, description="The cleaned value, if valid")
    issues: list[FieldIssue] = []


class CrossFieldIssue(BaseModel):
    rule_id: str
    fields: list[str]
    message: str


class ApplicationValidationResult(BaseModel):
    valid: bool
    missing_required: list[str]
    field_issues: dict[str, list[FieldIssue]]
    cross_field_issues: list[CrossFieldIssue]