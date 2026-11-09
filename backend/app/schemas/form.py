"""
Pydantic schemas for the form definition API.

The form itself lives in shared/schemas/application_schema.json. These shapes
describe how it is sent to the frontend and the agent: sections, fields with
bilingual labels, resolved option lists, conditional rules and field help
from the glossary.
"""

from typing import Any

from pydantic import BaseModel, Field


class LocalizedText(BaseModel):
    en: str
    kn: str


class FormOption(BaseModel):
    value: str
    label: LocalizedText


class ShowIf(BaseModel):
    """The field is shown only when `field` equals `equals`."""

    field: str
    equals: str


class FormField(BaseModel):
    id: str
    type: str = Field(
        ...,
        description="text, textarea, date, phone, email, number, currency, year, "
        "percentage, pincode, aadhaar, pan, choice, checkbox",
    )
    label: LocalizedText
    required: bool
    core: bool = False
    options: list[FormOption] = []
    show_if: ShowIf | None = None
    calculated: bool = False
    compare_with_document: bool = False
    validation: dict[str, Any] = {}


class FormSection(BaseModel):
    id: str
    title: LocalizedText
    fields: list[FormField]


class FormDefinition(BaseModel):
    form_id: str
    version: str
    sections: list[FormSection]


class FieldHelp(BaseModel):
    """Verified explanation of one field, from the glossary."""

    field_id: str
    language: str
    label: str
    explanation: str
    example: str
    where_to_find: str
    common_mistakes: list[str]