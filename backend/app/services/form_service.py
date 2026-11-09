"""
Form service: serves the form definition and field help.

Everything comes from shared/schemas/application_schema.json (form) and the
glossary files (help), so there is one source of truth for the frontend, the
validation engine and the agent.
"""

from functools import lru_cache

from ai_engine.intelligence import glossary
from app.core.exceptions import NotFoundError
from app.schemas.form import (
    FieldHelp,
    FormDefinition,
    FormField,
    FormOption,
    FormSection,
    LocalizedText,
    ShowIf,
)
from shared.constants import fields as F
from shared.constants.languages import normalize_language


@lru_cache(maxsize=1)
def get_form_definition() -> FormDefinition:
    schema = F.load_schema()
    sections: list[FormSection] = []

    for section in schema["sections"]:
        form_fields: list[FormField] = []
        for field in section["fields"]:
            options = [
                FormOption(
                    value=option["value"],
                    label=LocalizedText(en=option["en"], kn=option["kn"]),
                )
                for option in F.get_options(field["id"])
            ]
            form_fields.append(
                FormField(
                    id=field["id"],
                    type=field["type"],
                    label=LocalizedText(**field["label"]),
                    required=field["required"],
                    core=field.get("core", False),
                    options=options,
                    show_if=ShowIf(**field["show_if"]) if field.get("show_if") else None,
                    calculated=bool(field.get("calculated")),
                    compare_with_document=bool(field.get("compare_with_document")),
                    validation=field.get("validation", {}),
                )
            )
        sections.append(
            FormSection(
                id=section["id"],
                title=LocalizedText(**section["title"]),
                fields=form_fields,
            )
        )

    return FormDefinition(
        form_id=schema["form_id"], version=schema["version"], sections=sections
    )


def get_field_help(field_id: str, language: str = "en") -> FieldHelp:
    if not F.field_exists(field_id):
        raise NotFoundError(f"'{field_id}' is not a field in this form.")

    lang = normalize_language(language).value
    entry = glossary.get_field_entry(field_id, lang)
    if entry is None:
        raise NotFoundError("No help is available for this field.")

    return FieldHelp(
        field_id=field_id,
        language=lang,
        label=F.get_label(field_id, lang),
        explanation=entry["explanation"],
        example=entry["example"],
        where_to_find=entry["where_to_find"],
        common_mistakes=entry["common_mistakes"],
    )