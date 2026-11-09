"""Importing this package registers every model on Base.metadata."""

from app.models.application import Application, ApplicationStatus, FieldSource
from app.models.applicant import Applicant
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.conversation import ConversationMessage, MessageChannel, MessageRole
from app.models.event import ApplicationEvent, EventType

__all__ = [
    "Application", "ApplicationStatus", "FieldSource",
    "Applicant",
    "Document", "DocumentStatus", "DocumentType",
    "ConversationMessage", "MessageChannel", "MessageRole",
    "ApplicationEvent", "EventType",
]