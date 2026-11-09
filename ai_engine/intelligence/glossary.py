"""
Glossary lookup.

Single place that reads shared/glossary/english.json and kannada.json. The
form API and (later) the agent's get_field_help tool both use it, so
explanations always come from the verified glossary and are never invented.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

GLOSSARY_DIR = Path(__file__).resolve().parents[2] / "shared" / "glossary"

_FILES = {"en": "english.json", "kn": "kannada.json"}


@lru_cache(maxsize=4)
def load_glossary(language: str = "en") -> dict[str, Any]:
    filename = _FILES.get(language, _FILES["en"])
    with (GLOSSARY_DIR / filename).open(encoding="utf-8") as f:
        return json.load(f)


def get_field_entry(field_id: str, language: str = "en") -> dict[str, Any] | None:
    """Explanation, example, where_to_find and common_mistakes for a field,
    or None if the glossary has no entry."""
    return load_glossary(language)["fields"].get(field_id)


def get_term(term: str, language: str = "en") -> str | None:
    """Definition of a general term such as 'moratorium' or 'margin_money'."""
    return load_glossary(language)["terms"].get(term)


def list_terms(language: str = "en") -> list[str]:
    return list(load_glossary(language)["terms"])