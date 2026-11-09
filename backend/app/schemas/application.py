"""
Pydantic schemas for the application API.

These define what the frontend sends and receives. They are kept separate
from the database models so the API can change without touching the tables.
Whether a field ID actually exists and whether a value is valid is checked by
the services (they know the form schema), which return friendly issues
instead of a bare 422 error.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

LanguageCode = Literal["en", "kn"]
ApplicationStatusValue = Literal["draft", "in_progress", "ready_for_review", "submitted"]
AnswerSource = Literal["voice", "text"]  # document and calculated sources are set by the backend

# A form answer: text, number, yes/no checkbox, or empty (clears the field)
FieldValue = str | int | float | bool | None

FIELD_ID_PATTERN = r"^[a-z][a-z0-9_]*$"


# ---------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------
class ApplicationCreate(BaseModel):
    """Start a new application (language and consent from the entry screen)."""

    language: LanguageCode = "en"
    consent_given: bool = Field(
        ..., description="Must be true. Applicant agreed on the entry screen."
    )


class LanguageUpdate(BaseModel):
    language: LanguageCode


class FieldUpdate(BaseModel):
    """Save one answer."""

    field_id: str = Field(..., pattern=FIELD_ID_PATTERN, max_length=80)
    value: FieldValue
    source: AnswerSource = "text"


class FieldConfirm(BaseModel):
    """Confirm a field. Used for calculated fields and for resolving a
    conflict: send `value` to choose which value to keep, or leave it empty to
    confirm the value already stored."""

    field_id: str = Field(..., pattern=FIELD_ID_PATTERN, max_length=80)
    value: FieldValue = None


# ---------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------
class FieldIssue(BaseModel):
    """A problem with an answer, written for the applicant."""

    code: str = Field(..., description="Machine-readable code, e.g. invalid_format")
    message: str
    hint: str | None = Field(None, description="How to fix it, e.g. an example")
    suggested_field: str | None = Field(
        None, description="Another field this value seems to belong to"
    )

class SectionProgress(BaseModel):
    section_id: str
    answered: int
    total: int


class ProgressSummary(BaseModel):
    answered_required: int
    total_required: int
    percent: float = Field(..., ge=0, le=100)
    complete: bool
    sections: list[SectionProgress]


class ApplicationCreated(BaseModel):
    """Returned once when an application is created. The session token is
    shown only here; the server keeps just its hash."""

    application_id: str
    session_token: str
    status: ApplicationStatusValue
    language: LanguageCode


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: ApplicationStatusValue
    language: LanguageCode
    values: dict[str, Any]
    confirmed_fields: list[str]
    field_sources: dict[str, str]
    current_field: str | None
    consent_given: bool
    reference_id: str | None
    created_at: datetime
    updated_at: datetime
    progress: ProgressSummary | None = None


class FieldUpdateResult(BaseModel):
    """Result of saving one answer."""

    field_id: str
    accepted: bool
    value: FieldValue = Field(None, description="The value as stored (normalised)")
    issues: list[FieldIssue] = []
    auto_filled: dict[str, Any] = Field(
        default_factory=dict,
        description="Calculated fields updated as a result, e.g. percentage",
    )
    next_field: str | None = Field(None, description="The next field to ask about")
    progress: ProgressSummary | None = None
    
class InvalidField(BaseModel):
    """A required field whose latest attempt was rejected and that still has no
    accepted value."""

    field_id: str
    code: str
    message: str
    hint: str | None = None


class FieldStatus(BaseModel):
    """Every required, visible field falls into exactly one of these lists."""

    completed: list[str] = []
    pending: list[str] = []
    invalid: list[InvalidField] = []


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: ApplicationStatusValue
    language: LanguageCode
    values: dict[str, Any]
    confirmed_fields: list[str]
    field_sources: dict[str, str]
    current_field: str | None
    consent_given: bool
    reference_id: str | None
    created_at: datetime
    updated_at: datetime
    progress: ProgressSummary | None = None
    field_status: FieldStatus | None = None


class FieldUpdateResult(BaseModel):
    """Result of saving one answer."""

    field_id: str
    accepted: bool
    value: FieldValue = Field(None, description="The value as stored (normalised)")
    issues: list[FieldIssue] = []
    auto_filled: dict[str, Any] = Field(
        default_factory=dict,
        description="Calculated fields updated as a result, e.g. percentage",
    )
    next_field: str | None = Field(None, description="The next field to ask about")
    progress: ProgressSummary | None = None
    field_status: FieldStatus | None = None