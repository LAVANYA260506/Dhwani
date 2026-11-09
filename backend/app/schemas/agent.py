"""Pydantic schemas for the conversation endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.application import ApplicationRead, FieldIssue, FieldValue
from app.schemas.form import FieldHelp


class AgentTurnRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, description="What the applicant said or typed")
    source: Literal["voice", "text"] = "text"


class AgentField(BaseModel):
    field_id: str
    label: str
    value: FieldValue


class AgentRejection(BaseModel):
    field_id: str
    label: str
    issues: list[FieldIssue]


class AgentTurnResponse(BaseModel):
    reply: str = Field(..., description="Text to show")
    speech: str = Field(..., description="Text to speak (IDs spelled out character by character)")
    intent: str = Field(..., description="answer, question, confirm, reject, other")
    understood_by: Literal["llm", "rules", "none"] = "none"
    saved: list[AgentField] = []
    pending_confirmation: list[AgentField] = Field(
        [], description="Values waiting for the applicant to say yes or no"
    )
    rejected: list[AgentRejection] = []
    help: FieldHelp | None = None
    next_field: str | None = None
    application: ApplicationRead


class ConversationMessageRead(BaseModel):
    id: int
    role: str
    channel: str
    content: str
    field_id: str | None
    created_at: datetime


class ConversationHistory(BaseModel):
    messages: list[ConversationMessageRead]