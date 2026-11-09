"""Pydantic schemas for the review and mock-submission endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.application import FieldValue


class ReviewItem(BaseModel):
    field_id: str
    label: str
    display: str = Field(..., description="The value as the applicant should read it")
    value: FieldValue = None
    source: str | None = None
    confirmed: bool = False


class ReviewSection(BaseModel):
    id: str
    title: str
    items: list[ReviewItem]


class ReadinessIssue(BaseModel):
    kind: str = Field(..., description="missing, invalid or cross_field")
    field_id: str | None = None
    label: str | None = None
    section_id: str | None = None
    section_title: str | None = None
    message: str


class ReviewRead(BaseModel):
    status: str
    language: str
    ready: bool = Field(..., description="Every required field is complete and valid")
    can_submit: bool
    submitted: bool
    reference_id: str | None = None
    submitted_at: datetime | None = None
    issues: list[ReadinessIssue]
    sections: list[ReviewSection]


class SubmitRequest(BaseModel):
    confirm: bool = Field(..., description="Must be true: the applicant explicitly confirms")


class SubmitResult(BaseModel):
    reference_id: str
    submitted_at: datetime
    status: str
    already_submitted: bool = False