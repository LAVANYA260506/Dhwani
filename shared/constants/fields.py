"""
Field lookup helpers built on shared/schemas/application_schema.json.

The JSON schema is the single source of truth. Backend services, the
validation engine and the agent tools should use these helpers instead of
reading the JSON directly.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "application_schema.json"

Values = dict[str, Any]


# ---------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _fields_by_id() -> dict[str, dict[str, Any]]:
    return {f["id"]: f for s in load_schema()["sections"] for f in s["fields"]}


@lru_cache(maxsize=1)
def _section_of_field() -> dict[str, str]:
    return {f["id"]: s["id"] for s in load_schema()["sections"] for f in s["fields"]}


# ---------------------------------------------------------------------
# Basic lookups
# ---------------------------------------------------------------------
def get_sections() -> list[dict[str, Any]]:
    return load_schema()["sections"]


def get_section(section_id: str) -> dict[str, Any]:
    for section in get_sections():
        if section["id"] == section_id:
            return section
    raise KeyError(f"Unknown section: {section_id}")


def all_field_ids() -> list[str]:
    """Field IDs in form order."""
    return [f["id"] for s in get_sections() for f in s["fields"]]


def get_field(field_id: str) -> dict[str, Any]:
    try:
        return _fields_by_id()[field_id]
    except KeyError:
        raise KeyError(f"Unknown field: {field_id}") from None


def field_exists(field_id: str) -> bool:
    return field_id in _fields_by_id()


def get_section_id_for_field(field_id: str) -> str:
    get_field(field_id)  # raises if unknown
    return _section_of_field()[field_id]


def get_label(field_id: str, lang: str = "en") -> str:
    label = get_field(field_id)["label"]
    return label.get(lang) or label["en"]


def get_section_title(section_id: str, lang: str = "en") -> str:
    title = get_section(section_id)["title"]
    return title.get(lang) or title["en"]


# ---------------------------------------------------------------------
# Options (choice fields)
# ---------------------------------------------------------------------
def get_options(field_id: str) -> list[dict[str, str]]:
    """Options for a choice field, or an empty list for other types."""
    key = get_field(field_id).get("options")
    if not key:
        return []
    return load_schema()["option_sets"][key]


def get_option_values(field_id: str) -> list[str]:
    return [o["value"] for o in get_options(field_id)]


def get_option_label(field_id: str, value: str, lang: str = "en") -> str | None:
    for option in get_options(field_id):
        if option["value"] == value:
            return option.get(lang) or option["en"]
    return None


# ---------------------------------------------------------------------
# Field groups
# ---------------------------------------------------------------------
def core_field_ids() -> list[str]:
    return [i for i in all_field_ids() if get_field(i).get("core")]


def document_compare_field_ids() -> list[str]:
    """Fields compared with the extracted marks card."""
    return [i for i in all_field_ids() if get_field(i).get("compare_with_document")]


def calculated_fields() -> dict[str, dict[str, Any]]:
    """Map of calculated field ID to its calculation spec."""
    return {
        i: get_field(i)["calculated"]
        for i in all_field_ids()
        if get_field(i).get("calculated")
    }


def get_cross_field_rules() -> list[dict[str, Any]]:
    return load_schema()["cross_field_rules"]


# ---------------------------------------------------------------------
# Conditional visibility and completion
# ---------------------------------------------------------------------
def is_answered(field_id: str, value: Any) -> bool:
    """True if the value counts as an answer for this field."""
    if value is None:
        return False
    if get_field(field_id)["type"] == "checkbox":
        return value is True
    if isinstance(value, str):
        return value.strip() != ""
    return True


def is_visible(field_id: str, values: Values) -> bool:
    """A field with show_if is visible only when its trigger field matches."""
    condition = get_field(field_id).get("show_if")
    if not condition:
        return True
    return values.get(condition["field"]) == condition["equals"]


def visible_field_ids(values: Values) -> list[str]:
    return [i for i in all_field_ids() if is_visible(i, values)]


def required_field_ids(values: Values, include_calculated: bool = False) -> list[str]:
    """Visible required fields. Calculated fields are excluded by default
    because the applicant does not answer them directly."""
    result = []
    for field_id in visible_field_ids(values):
        field = get_field(field_id)
        if not field.get("required"):
            continue
        if field.get("calculated") and not include_calculated:
            continue
        result.append(field_id)
    return result


def missing_required_field_ids(values: Values) -> list[str]:
    return [i for i in required_field_ids(values) if not is_answered(i, values.get(i))]


def next_field_to_ask(values: Values, include_optional: bool = False) -> str | None:
    """First visible, unanswered, non-calculated field in form order."""
    for field_id in visible_field_ids(values):
        field = get_field(field_id)
        if field.get("calculated"):
            continue
        if not field.get("required") and not include_optional:
            continue
        if not is_answered(field_id, values.get(field_id)):
            return field_id
    return None


def section_progress(values: Values) -> dict[str, dict[str, int]]:
    """Per-section counts of required fields answered vs total (visible only)."""
    progress: dict[str, dict[str, int]] = {}
    required = set(required_field_ids(values))
    for section in get_sections():
        ids = [f["id"] for f in section["fields"] if f["id"] in required]
        done = sum(1 for i in ids if is_answered(i, values.get(i)))
        progress[section["id"]] = {"answered": done, "total": len(ids)}
    return progress