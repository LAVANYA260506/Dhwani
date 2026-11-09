"""
Understanding an utterance: which fields did the applicant answer, or are they
asking a question?

    result = extract("My PAN is ABCPE1234F and I was born 14 May 2003", "en", "full_name", values)
    result.intent         # "answer" | "question" | "other"
    result.fields         # {"pan_number": "ABCPE1234F", "date_of_birth": "2003-05-14"}
    result.question_field # field the applicant is asking about
    result.source         # "llm" or "rules"

The language model proposes; nothing here saves anything. Every proposed value
still goes through the validation engine and the save path. If the model fails
or returns nothing useful, a rule-based extractor takes over, so voice keeps
working without the LLM (it cannot find names or free text, so it treats a
bare reply as the answer to the current field).
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from ai_engine.agent import prompts
from ai_engine.intelligence import bank_info
from ai_engine.agent.llm_client import LLMError, generate_json
from shared.constants import fields as F

logger = logging.getLogger("dhwani.agent")

MAX_FIELDS = 12
INTENTS = {"answer", "question", "info", "repeat", "other"}


@dataclass
class Extraction:
    intent: str = "other"
    fields: dict[str, Any] = field(default_factory=dict)
    question_field: str | None = None
    source: str = "rules"
    llm_error: str | None = None  # why the model was not used, if it was not
    info_topic: str | None = None  # for intent "info": which topic was asked about

# ---------------------------------------------------------------------
# Language model path
# ---------------------------------------------------------------------
def _clean_fields(raw: Any, values: dict[str, Any]) -> dict[str, Any]:
    """Keep only real, fillable fields with simple values. Visibility is
    judged against the saved answers plus this same utterance, so "abroad, in
    Germany" can fill both the place of study and the country."""
    if not isinstance(raw, dict):
        return {}
    merged = {**values, **{k: v for k, v in raw.items() if isinstance(k, str)}}

    cleaned: dict[str, Any] = {}
    for field_id, value in raw.items():
        if not isinstance(field_id, str) or not F.field_exists(field_id):
            continue
        definition = F.get_field(field_id)
        if definition.get("calculated") or not F.is_visible(field_id, merged):
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        elif value is None or not isinstance(value, (bool, int, float)):
            continue
        cleaned[field_id] = value
        if len(cleaned) >= MAX_FIELDS:
            break
    return cleaned


def _from_llm(raw: dict[str, Any], current_field: str | None, values: dict[str, Any]) -> Extraction:
    intent = raw.get("intent") if raw.get("intent") in INTENTS else "other"
    if intent == "info":
        topic = raw.get("info_topic")
        return Extraction(
            intent="info",
            info_topic=topic if topic in bank_info.TOPIC_IDS else "unknown",
            source="llm",
        )
    fields = _clean_fields(raw.get("fields"), values)

    question_field = raw.get("question_field")
    if not (isinstance(question_field, str) and F.field_exists(question_field)):
        question_field = current_field if intent == "question" else None

    if intent == "repeat":
        question_field = current_field
    
    if fields and intent == "other":
        intent = "answer"
    return Extraction(intent=intent, fields=fields, question_field=question_field, source="llm")


# ---------------------------------------------------------------------
# Rule-based path (fallback)
# ---------------------------------------------------------------------
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_SPOKEN_EMAIL = re.compile(
    r"(?<![\w.])([a-z0-9._-]+)\s+at(?:\s+the\s+rate)?\s+([a-z0-9-]+)\s+dot\s+"
    r"([a-z]{2,}(?:\s+dot\s+[a-z]{2,})*)",
    re.IGNORECASE,
)
_PAN = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{5}\d{4}[A-Za-z](?![A-Za-z0-9])")
_AADHAAR = re.compile(r"(?<!\d)[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
_PHONE = re.compile(r"(?<!\d)(?:\+91[\s-]?|0)?[6-9]\d{9}(?!\d)")
_DATE = re.compile(
    r"(?<!\d)\d{1,2}[-/.]\d{1,2}[-/.]\d{4}(?!\d)"
    r"|(?<!\d)\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9},?\s+\d{4}"
)
_PIN = re.compile(r"(?<!\d)[1-9]\d{5}(?!\d)")

# (field type, pattern), in an order that stops one pattern eating another's digits
_PATTERNS = [
    ("email", _EMAIL),
    ("pan", _PAN),
    ("date", _DATE),
    ("aadhaar", _AADHAAR),
    ("phone", _PHONE),
    ("pincode", _PIN),
]

_QUESTION_WORDS = {
    "what", "why", "how", "which", "where", "explain", "mean", "meaning",
    "means", "example", "format", "help", "ಏನು", "ಯಾಕೆ", "ಯಾಕೆ", "ಹೇಗೆ",
    "ಅರ್ಥ", "ಉದಾಹರಣೆ", "ಎಲ್ಲಿ", "ಯಾವುದು", "ಸಹಾಯ",
}
_LEAD_IN = re.compile(
    r"^\s*(?:my\s+\w+(?:\s+\w+)?\s+is|it\s+is|it's|this\s+is|i\s+am|i'm|the\s+answer\s+is)\s+",
    re.IGNORECASE,
)


def _target_for(kind: str, current_field: str | None, values: dict[str, Any], used: set[str]) -> str | None:
    """Which field a value of this type belongs to: the one being asked about
    if it matches, otherwise the first unanswered visible field of that type."""
    def ok(field_id: str) -> bool:
        return (
            field_id not in used
            and F.field_exists(field_id)
            and F.get_field(field_id)["type"] == kind
            and not F.get_field(field_id).get("calculated")
            and F.is_visible(field_id, values)
        )

    if current_field and ok(current_field):
        return current_field
    candidates = [f for f in F.visible_field_ids(values) if ok(f)]
    for field_id in candidates:
        if not F.is_answered(field_id, values.get(field_id)):
            return field_id
    return candidates[0] if candidates else None


def _looks_like_question(text: str) -> bool:
    if "?" in text:
        return True
    words = {w.strip(".,;:!\"'()").casefold() for w in text.split()}
    return bool(words & _QUESTION_WORDS)


def extract_by_rules(
    utterance: str, language: str, current_field: str | None, values: dict[str, Any]
) -> Extraction:
    text = " ".join(utterance.split())
    remaining = text
    found: dict[str, Any] = {}
    used: set[str] = set()

    # Spoken emails ("lavanya at gmail dot com") become real addresses first
    def _join_email(match: re.Match) -> str:
        domain = re.sub(r"\s+dot\s+", ".", match.group(3), flags=re.IGNORECASE)
        return f"{match.group(1)}@{match.group(2)}.{domain}".lower()

    remaining = _SPOKEN_EMAIL.sub(_join_email, remaining)

    for kind, pattern in _PATTERNS:
        for match in list(pattern.finditer(remaining)):
            target = _target_for(kind, current_field, {**values, **found}, used)
            if target is None:
                continue
            found[target] = match.group(0).strip()
            used.add(target)
        remaining = pattern.sub(" ", remaining)

    if found:
        return Extraction(intent="answer", fields=found, source="rules")

    topic = bank_info.detect_topic(text)
    if topic:
        return Extraction(intent="info", info_topic=topic, source="rules")
    
    if _looks_like_question(text):
        return Extraction(intent="question", question_field=current_field, source="rules")

    if current_field and F.field_exists(current_field) and text:
        definition = F.get_field(current_field)
        if not definition.get("calculated") and F.is_visible(current_field, values):
            answer = _LEAD_IN.sub("", text).strip(" .,")
            too_long = definition["type"]=="text" and len(answer.split()) >10
            if answer and not too_long:
                return Extraction(intent="answer", fields={current_field: answer}, source="rules")

    return Extraction(intent="other", source="rules")


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------
def extract(
    utterance: str, language: str, current_field: str | None, values: dict[str, Any]
) -> Extraction:
    """Understand one utterance. Uses the language model, and the rule-based
    extractor when the model fails or finds nothing."""
    utterance = utterance.strip()
    if not utterance:
        return Extraction(intent="other", source="rules")

    try:
        raw = generate_json(
            prompts.SYSTEM_PROMPT,
            prompts.build_user_message(utterance, language, current_field, values),
        )
        result = _from_llm(raw, current_field, values)
    except LLMError as error:
        logger.warning("extraction fell back to rules: %s", error)
        result = extract_by_rules(utterance, language, current_field, values)
        result.llm_error = error.kind
        return result

    if not result.fields and result.intent not in ("question", "repeat", "info"):
        fallback = extract_by_rules(utterance, language, current_field, values)
        if fallback.fields or fallback.intent == "question":
            return fallback
    return result