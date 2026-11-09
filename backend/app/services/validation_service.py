"""
Validation engine: deterministic checks for every field.

    validate_field(field_id, value, values, language)  -> (clean_value, issues)
    find_cross_violations(values, language, changed_field)
    validate_application(values, language)             -> missing, field issues, cross issues

Rules come from shared/schemas/application_schema.json (field type, the
"validation" block and "cross_field_rules"), so the form and the checks never
drift apart. Every issue is written for the applicant, in English or Kannada,
with a hint on how to fix it. The LLM never decides what is valid; it only
relays these results.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable

from app.schemas.application import FieldIssue
from shared.constants import fields as F
from shared.constants.languages import normalize_digits

# ---------------------------------------------------------------------
# Messages: code -> language -> (message, hint)
# ---------------------------------------------------------------------
MESSAGES: dict[str, dict[str, tuple[str, str | None]]] = {
    "unknown_field": {
        "en": ("That is not a field in this form.", None),
        "kn": ("ಇದು ಈ ಅರ್ಜಿಯಲ್ಲಿರುವ ಕ್ಷೇತ್ರವಲ್ಲ.", None),
    },
    "required": {
        "en": ("This information is required.", None),
        "kn": ("ಈ ಮಾಹಿತಿ ಅಗತ್ಯ.", None),
    },
    "invalid_text": {
        "en": ("Please enter text for this field.", None),
        "kn": ("ಈ ಕ್ಷೇತ್ರಕ್ಕೆ ಪಠ್ಯವನ್ನು ನಮೂದಿಸಿ.", None),
    },
    "too_short": {
        "en": ("This is too short. Please enter at least {min} characters.", None),
        "kn": ("ಇದು ತುಂಬಾ ಚಿಕ್ಕದಾಗಿದೆ. ಕನಿಷ್ಠ {min} ಅಕ್ಷರಗಳನ್ನು ನಮೂದಿಸಿ.", None),
    },
    "too_long": {
        "en": ("This is too long. Please use at most {max} characters.", None),
        "kn": ("ಇದು ತುಂಬಾ ಉದ್ದವಾಗಿದೆ. ಗರಿಷ್ಠ {max} ಅಕ್ಷರಗಳನ್ನು ಮಾತ್ರ ಬಳಸಿ.", None),
    },
    "invalid_name": {
        "en": ("A name should contain only letters.", "Example: Lavanya A"),
        "kn": ("ಹೆಸರಿನಲ್ಲಿ ಅಕ್ಷರಗಳು ಮಾತ್ರ ಇರಬೇಕು.", "ಉದಾಹರಣೆ: ಲಕ್ಷ್ಮಿ ಕೆ"),
    },
    "invalid_register_number": {
        "en": (
            "A register number can contain only letters, digits, / and -.",
            "Example: 1SJ21CS045",
        ),
        "kn": (
            "ನೋಂದಣಿ ಸಂಖ್ಯೆಯಲ್ಲಿ ಅಕ್ಷರಗಳು, ಅಂಕಿಗಳು, / ಮತ್ತು - ಮಾತ್ರ ಇರಬಹುದು.",
            "ಉದಾಹರಣೆ: 1SJ21CS045",
        ),
    },
    "invalid_phone": {
        "en": (
            "A mobile number has 10 digits and starts with 6, 7, 8 or 9.",
            "Example: 9876543210",
        ),
        "kn": (
            "ಮೊಬೈಲ್ ಸಂಖ್ಯೆಯಲ್ಲಿ 10 ಅಂಕಿಗಳಿರುತ್ತವೆ ಮತ್ತು ಅದು 6, 7, 8 ಅಥವಾ 9 ರಿಂದ ಆರಂಭವಾಗುತ್ತದೆ.",
            "ಉದಾಹರಣೆ: 9876543210",
        ),
    },
    "invalid_email": {
        "en": (
            "That does not look like a valid email address.",
            "Example: name@example.com",
        ),
        "kn": (
            "ಇದು ಮಾನ್ಯ ಇಮೇಲ್ ವಿಳಾಸದಂತೆ ಕಾಣುತ್ತಿಲ್ಲ.",
            "ಉದಾಹರಣೆ: name@example.com",
        ),
    },
    "invalid_pincode": {
        "en": ("A PIN code has exactly 6 digits.", "Example: 560001"),
        "kn": ("ಪಿನ್ ಕೋಡ್‌ನಲ್ಲಿ ಸರಿಯಾಗಿ 6 ಅಂಕಿಗಳಿರುತ್ತವೆ.", "ಉದಾಹರಣೆ: 560001"),
    },
    "invalid_pan": {
        "en": (
            "A PAN has 10 characters: 5 letters, 4 digits, then 1 letter.",
            "Example: ABCPE1234F",
        ),
        "kn": (
            "ಪ್ಯಾನ್ 10 ಅಕ್ಷರಗಳನ್ನು ಹೊಂದಿರುತ್ತದೆ: 5 ಅಕ್ಷರ, 4 ಅಂಕಿ, ನಂತರ 1 ಅಕ್ಷರ.",
            "ಉದಾಹರಣೆ: ABCPE1234F",
        ),
    },
    "invalid_aadhaar": {
        "en": ("An Aadhaar number has exactly 12 digits.", "Example: 2345 6789 0123"),
        "kn": (
            "ಆಧಾರ್ ಸಂಖ್ಯೆಯಲ್ಲಿ ಸರಿಯಾಗಿ 12 ಅಂಕಿಗಳಿರುತ್ತವೆ.",
            "ಉದಾಹರಣೆ: 2345 6789 0123",
        ),
    },
    "invalid_date": {
        "en": (
            "I could not read that as a date.",
            "Give it as day, month, year, for example 14-05-2003.",
        ),
        "kn": (
            "ಇದನ್ನು ದಿನಾಂಕವಾಗಿ ಓದಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ.",
            "ದಿನ, ತಿಂಗಳು, ವರ್ಷ ಕ್ರಮದಲ್ಲಿ ನೀಡಿ, ಉದಾಹರಣೆ: 14-05-2003.",
        ),
    },
    "date_in_future": {
        "en": ("This date is in the future.", "Please check the date."),
        "kn": ("ಈ ದಿನಾಂಕ ಭವಿಷ್ಯದಲ್ಲಿದೆ.", "ದಯವಿಟ್ಟು ದಿನಾಂಕವನ್ನು ಪರಿಶೀಲಿಸಿ."),
    },
    "age_out_of_range": {
        "en": (
            "That date makes the age {age}. It must be between {min} and {max} years.",
            "Please check the date of birth.",
        ),
        "kn": (
            "ಈ ದಿನಾಂಕದ ಪ್ರಕಾರ ವಯಸ್ಸು {age} ಆಗುತ್ತದೆ. ಅದು {min} ರಿಂದ {max} ವರ್ಷಗಳ ನಡುವೆ ಇರಬೇಕು.",
            "ಹುಟ್ಟಿದ ದಿನಾಂಕವನ್ನು ಪರಿಶೀಲಿಸಿ.",
        ),
    },
    "invalid_year": {
        "en": ("Please enter a 4-digit year.", "Example: 2024"),
        "kn": ("4 ಅಂಕಿಗಳ ವರ್ಷವನ್ನು ನಮೂದಿಸಿ.", "ಉದಾಹರಣೆ: 2024"),
    },
    "invalid_number": {
        "en": (
            "Please enter a number using digits only.",
            "Example: 85.5 or 700000. You can also say '5 lakh'.",
        ),
        "kn": (
            "ಅಂಕಿಗಳನ್ನು ಮಾತ್ರ ಬಳಸಿ ಸಂಖ್ಯೆಯನ್ನು ನಮೂದಿಸಿ.",
            "ಉದಾಹರಣೆ: 85.5 ಅಥವಾ 700000.",
        ),
    },
    "not_integer": {
        "en": ("Please enter a whole number.", "Example: 3"),
        "kn": ("ಪೂರ್ಣ ಸಂಖ್ಯೆಯನ್ನು ನಮೂದಿಸಿ.", "ಉದಾಹರಣೆ: 3"),
    },
    "below_minimum": {
        "en": ("This must be at least {min}.", None),
        "kn": ("ಇದು ಕನಿಷ್ಠ {min} ಇರಬೇಕು.", None),
    },
    "above_maximum": {
        "en": ("This must be at most {max}.", None),
        "kn": ("ಇದು ಗರಿಷ್ಠ {max} ಇರಬೇಕು.", None),
    },
    "invalid_choice": {
        "en": ("That is not one of the available options.", "Choose one of: {options}"),
        "kn": (
            "ಇದು ಲಭ್ಯವಿರುವ ಆಯ್ಕೆಗಳಲ್ಲಿ ಒಂದಲ್ಲ.",
            "ಇವುಗಳಲ್ಲಿ ಒಂದನ್ನು ಆರಿಸಿ: {options}",
        ),
    },
    "invalid_yes_no": {
        "en": ("Please answer yes or no.", None),
        "kn": ("ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಉತ್ತರಿಸಿ.", None),
    },
    "must_accept": {
        "en": ("You need to agree to this to continue.", None),
        "kn": ("ಮುಂದುವರಿಯಲು ನೀವು ಇದಕ್ಕೆ ಒಪ್ಪಬೇಕು.", None),
    },
    "wrong_field": {
        "en": (
            "That looks like {kind}, but I was asking for: {field}.",
            "I can save it under '{suggested_label}' instead.",
        ),
        "kn": (
            "ಇದು {kind} ಆಗಿರುವಂತೆ ಕಾಣುತ್ತಿದೆ, ಆದರೆ ನಾನು ಕೇಳುತ್ತಿದ್ದದ್ದು: {field}.",
            "ಬದಲಿಗೆ ಅದನ್ನು '{suggested_label}' ಅಡಿಯಲ್ಲಿ ಉಳಿಸಬಲ್ಲೆ.",
        ),
    },
    "cross_field": {
        "en": ("These answers do not agree with each other.", None),
        "kn": ("ಈ ಉತ್ತರಗಳು ಪರಸ್ಪರ ಹೊಂದಿಕೆಯಾಗುತ್ತಿಲ್ಲ.", None),
    },
}

KIND_NAMES = {
    "phone": {"en": "a mobile number", "kn": "ಮೊಬೈಲ್ ಸಂಖ್ಯೆ"},
    "email": {"en": "an email address", "kn": "ಇಮೇಲ್ ವಿಳಾಸ"},
    "pincode": {"en": "a PIN code", "kn": "ಪಿನ್ ಕೋಡ್"},
    "aadhaar": {"en": "an Aadhaar number", "kn": "ಆಧಾರ್ ಸಂಖ್ಯೆ"},
    "pan": {"en": "a PAN number", "kn": "ಪ್ಯಾನ್ ಸಂಖ್ಯೆ"},
    "date": {"en": "a date", "kn": "ದಿನಾಂಕ"},
}

# What kind of value each field type expects (None = free text or number)
TYPE_KIND = {
    "phone": "phone",
    "email": "email",
    "pincode": "pincode",
    "pan": "pan",
    "aadhaar": "aadhaar",
    "date": "date",
}
# Where a value of a given kind normally belongs (first free visible field wins)
KIND_FIELDS = {
    "phone": ["mobile_number", "alternate_mobile", "co_applicant_mobile"],
    "email": ["email"],
    "pincode": ["current_pincode"],
    "aadhaar": ["aadhaar_number"],
    "pan": ["pan_number", "co_applicant_pan"],
    "date": ["date_of_birth", "co_applicant_dob"],
}
# Kinds that are never plausible as ordinary text, so they are flagged even in
# text fields. PIN codes and dates are not (they can appear inside an address).
STRONG_KINDS = {"email", "pan", "phone", "aadhaar"}

NAME_FIELDS = {
    "full_name", "father_name", "mother_name", "co_applicant_name", "guarantor_name",
}
INTEGER_FIELDS = {"entrance_exam_rank", "backlog_count"}
# Register numbers can legitimately look like phone numbers
NO_WRONG_FIELD_CHECK = {"register_number"}

TRUE_WORDS = {
    "true", "yes", "y", "yeah", "yep", "ok", "1",
    "haudu", "houdu", "sari", "ಹೌದು", "ಸರಿ",
}
FALSE_WORDS = {
    "false", "no", "n", "nope", "0", "illa", "beda",
    "ಇಲ್ಲ", "ಬೇಡ",
}
_WORD_STRIP = ".,;:!?\"'()[]"

# TRUE_WORDS = {"true", "yes", "y", "yeah", "yep", "ok", "1", "ಹೌದು"}
# FALSE_WORDS = {"false", "no", "n", "nope", "0", "ಇಲ್ಲ"}


def _lang(language: str) -> str:
    return "kn" if language == "kn" else "en"


def _issue(
    code: str, language: str, suggested: str | None = None, **params: Any
) -> FieldIssue:
    message, hint = MESSAGES[code].get(language) or MESSAGES[code]["en"]
    return FieldIssue(
        code=code,
        message=message.format(**params),
        hint=hint.format(**params) if hint else None,
        suggested_field=suggested,
    )


def _fmt(number: Any, grouped: bool = True) -> str:
    if isinstance(number, float) and number.is_integer():
        number = int(number)
    if isinstance(number, int) and grouped:
        return f"{number:,}"
    return str(number)


# ---------------------------------------------------------------------
# Detecting what a value looks like (for wrong-field detection)
# ---------------------------------------------------------------------
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PAN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def detect_kind(text: str) -> str | None:
    """Guess what kind of value this is: phone, email, pincode, aadhaar, pan,
    date, or None."""
    text = text.strip()
    if _EMAIL.match(text):
        return "email"
    if _PAN.match(re.sub(r"\s", "", text).upper()):
        return "pan"
    digits = re.sub(r"[\s\-().]", "", text)
    if re.fullmatch(r"[2-9]\d{11}", digits) and not text.startswith("+"):
        return "aadhaar"
    if _normalise_phone(text) is not None:
        return "phone"
    if re.fullmatch(r"[1-9]\d{5}", digits):
        return "pincode"
    if not text.isdigit() and parse_date(text) is not None:
        return "date"
    return None


def _suggest_field(kind: str, values: dict[str, Any]) -> str | None:
    candidates = [
        c for c in KIND_FIELDS.get(kind, [])
        if F.field_exists(c) and F.is_visible(c, values)
    ]
    if not candidates:
        return None
    for candidate in candidates:
        if not F.is_answered(candidate, values.get(candidate)):
            return candidate
    return candidates[0]


def _wrong_field_issue(
    field_id: str,
    field_type: str,
    value: Any,
    values: dict[str, Any],
    lang: str,
    strong_only: bool = False,
) -> FieldIssue | None:
    if field_id in NO_WRONG_FIELD_CHECK or value is None or isinstance(value, bool):
        return None
    kind = detect_kind(str(value))
    if kind is None or kind == TYPE_KIND.get(field_type):
        return None
    if strong_only and kind not in STRONG_KINDS:
        return None

    suggested = _suggest_field(kind, values)
    issue = _issue(
        "wrong_field",
        lang,
        suggested=suggested,
        kind=KIND_NAMES[kind][lang],
        field=F.get_label(field_id, lang),
        suggested_label=F.get_label(suggested, lang) if suggested else "",
    )
    if not suggested:
        issue.hint = None
    return issue


# ---------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------
def _normalise_phone(value: Any) -> str | None:
    digits = re.sub(r"[\s\-().]", "", str(value))
    if digits.startswith("+91"):
        digits = digits[3:]
    elif len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits if re.fullmatch(r"[6-9]\d{9}", digits) else None


_DATE_FORMATS = [
    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d %m %Y",
    "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y",
    "%Y %B %d", "%Y %b %d",
]

# Kannada month names (and common spelling variants) -> English
_KANNADA_MONTHS = {
    "ಜನವರಿ": "January", "ಜನೆವರಿ": "January",
    "ಫೆಬ್ರವರಿ": "February", "ಫೆಬ್ರುವರಿ": "February",
    "ಮಾರ್ಚ್": "March", "ಮಾರ್ಚ": "March",
    "ಏಪ್ರಿಲ್": "April", "ಏಪ್ರಿಲ": "April",
    "ಮೇ": "May",
    "ಜೂನ್": "June", "ಜೂನ": "June",
    "ಜುಲೈ": "July",
    "ಆಗಸ್ಟ್": "August", "ಆಗಸ್ಟ": "August",
    "ಸೆಪ್ಟೆಂಬರ್": "September", "ಸೆಪ್ಟಂಬರ್": "September",
    "ಅಕ್ಟೋಬರ್": "October", "ಅಕ್ಟೊಬರ್": "October",
    "ನವೆಂಬರ್": "November", "ನವೆಂಬರ": "November",
    "ಡಿಸೆಂಬರ್": "December", "ಡಿಸೆಂಬರ": "December",
}
_DATE_NOISE = {"ತಿಂಗಳು", "ರಂದು", "ತಾರೀಖು", "ದಿನಾಂಕ", "ಇಸವಿ"}


def parse_date(text: str) -> date | None:
    """Read a date typed or spoken as 14-05-2003, 14/5/2003, 14 May 2003,
    6 ಮೇ 2006, ನವೆಂಬರ್ 3, 2013 ..."""
    text = re.sub(r"(\d)(?:st|nd|rd|th)\b", r"\1", text.strip(), flags=re.IGNORECASE)
    tokens = []
    for token in text.replace(",", " ").split():
        word = token.strip(".;:!?")
        if word in _DATE_NOISE:
            continue
        tokens.append(_KANNADA_MONTHS.get(word, word))
    text = " ".join(tokens)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


_MULTIPLIERS = {
    "thousand": 1_000, "k": 1_000,
    "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000,
    "crore": 10_000_000, "crores": 10_000_000,
}
_WORD_NUMBER = re.compile(r"^(\d+(?:\.\d+)?)(thousand|k|lakhs?|lacs?|crores?)$")
_PLAIN_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


def _to_number(value: Any) -> int | float | None:
    """Turn typed or spoken input into a number, or None if it is not one."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number: int | float = value
    else:
        text = str(value).lower()
        for noise in ("\u20b9", "rupees", "rupee", "rs.", "rs", "inr", "%", ",", " "):
            text = text.replace(noise, "")
        match = _WORD_NUMBER.match(text)
        if match:
            number = float(match.group(1)) * _MULTIPLIERS[match.group(2)]
        elif _PLAIN_NUMBER.match(text):
            number = float(text)
        else:
            return None
    if isinstance(number, float) and number.is_integer():
        number = int(number)
    return number


def _resolve_bound(bound: Any) -> int | float | None:
    """A bound in the schema is a number or 'current_year' / 'current_year+1'."""
    if bound is None:
        return None
    if isinstance(bound, (int, float)):
        return bound
    match = re.fullmatch(r"current_year(?:\s*([+-])\s*(\d+))?", str(bound))
    if match:
        year = date.today().year
        if match.group(1):
            year += int(match.group(2)) * (1 if match.group(1) == "+" else -1)
        return year
    return None


def _age(born: date, today: date) -> int:
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _is_name(text: str) -> bool:
    """Letters (any script, including Kannada marks), spaces . ' -"""
    has_letter = False
    for ch in text:
        if ch.isalpha():
            has_letter = True
        elif ch in " .'-" or unicodedata.category(ch)[0] == "M" or unicodedata.category(ch) == "Cf":
            continue
        else:
            return False
    return has_letter


# ---------------------------------------------------------------------
# Validators, one per field type: (field_id, type, rules, value, lang)
#                                  -> (clean_value, issues)
# ---------------------------------------------------------------------
Result = tuple[Any, list[FieldIssue]]


def _v_text(field_id: str, ftype: str, rules: dict, value: Any, lang: str) -> Result:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None, [_issue("invalid_text", lang)]
    text = " ".join(str(value).split())
    if not text:
        return None, [_issue("required", lang)]

    if field_id in NAME_FIELDS and not _is_name(text):
        return None, [_issue("invalid_name", lang)]
    if field_id == "register_number":
        text = text.replace(" ", "").upper()
        if not re.fullmatch(r"[A-Z0-9/\-]+", text):
            return None, [_issue("invalid_register_number", lang)]

    if "min_length" in rules and len(text) < rules["min_length"]:
        return None, [_issue("too_short", lang, min=rules["min_length"])]
    if "max_length" in rules and len(text) > rules["max_length"]:
        return None, [_issue("too_long", lang, max=rules["max_length"])]
    return text, []


def _v_phone(field_id: str, ftype: str, rules: dict, value: Any, lang: str) -> Result:
    phone = _normalise_phone(value)
    return (phone, []) if phone else (None, [_issue("invalid_phone", lang)])


def _v_email(field_id: str, ftype: str, rules: dict, value: Any, lang: str) -> Result:
    text = str(value).strip().lower()
    if "@" not in text:
        # Spoken form: "lavanya at gmail dot com"
        text = re.sub(r"\s+(?:at the rate|at)\s+", "@", text)
        text = re.sub(r"\s+dot\s+", ".", text)
    text = text.replace(" ", "")
    if _EMAIL.match(text) and len(text) <= 120:
        return text, []
    return None, [_issue("invalid_email", lang)]


def _v_pincode(field_id: str, ftype: str, rules: dict, value: Any, lang: str) -> Result:
    digits = re.sub(r"[\s\-]", "", str(value))
    if re.fullmatch(r"[1-9]\d{5}", digits):
        return digits, []
    return None, [_issue("invalid_pincode", lang)]


def _v_pan(field_id: str, ftype: str, rules: dict, value: Any, lang: str) -> Result:
    text = re.sub(r"\s", "", str(value)).upper()
    # 4th character is the holder type (P = individual, C = company, ...)
    if _PAN.match(text) and text[3] in "PCHFATBLJG":
        return text, []
    return None, [_issue("invalid_pan", lang)]


def _v_aadhaar(field_id: str, ftype: str, rules: dict, value: Any, lang: str) -> Result:
    # Format only. The Verhoeff checksum is skipped for the prototype.
    digits = re.sub(r"[\s\-]", "", str(value))
    if re.fullmatch(r"[2-9]\d{11}", digits):
        return digits, []
    return None, [_issue("invalid_aadhaar", lang)]


def _v_date(field_id: str, ftype: str, rules: dict, value: Any, lang: str) -> Result:
    parsed = parse_date(str(value))
    if parsed is None:
        return None, [_issue("invalid_date", lang)]
    today = date.today()
    if parsed > today:
        return None, [_issue("date_in_future", lang)]

    min_age, max_age = rules.get("min_age"), rules.get("max_age")
    if min_age is not None or max_age is not None:
        age = _age(parsed, today)
        if (min_age is not None and age < min_age) or (max_age is not None and age > max_age):
            return None, [
                _issue("age_out_of_range", lang, age=age, min=min_age or 0, max=max_age or 120)
            ]
    return parsed.isoformat(), []


def _range_issues(number: int | float, rules: dict, lang: str, grouped: bool = True) -> list[FieldIssue]:
    low, high = _resolve_bound(rules.get("min")), _resolve_bound(rules.get("max"))
    if low is not None and number < low:
        return [_issue("below_minimum", lang, min=_fmt(low, grouped))]
    if high is not None and number > high:
        return [_issue("above_maximum", lang, max=_fmt(high, grouped))]
    return []


def _v_year(field_id: str, ftype: str, rules: dict, value: Any, lang: str) -> Result:
    number = _to_number(value)
    if number is None or not isinstance(number, int) or not 1000 <= number <= 9999:
        return None, [_issue("invalid_year", lang)]
    issues = _range_issues(number, rules, lang, grouped=False)
    return (None, issues) if issues else (number, [])


def _v_number(field_id: str, ftype: str, rules: dict, value: Any, lang: str) -> Result:
    number = _to_number(value)
    if number is None:
        return None, [_issue("invalid_number", lang)]
    if field_id in INTEGER_FIELDS and not isinstance(number, int):
        return None, [_issue("not_integer", lang)]
    if ftype == "percentage":
        rules = {"min": 0, "max": 100, **rules}
    issues = _range_issues(number, rules, lang)
    return (None, issues) if issues else (number, [])


# def _v_choice(field_id: str, ftype: str, rules: dict, value: Any, lang: str) -> Result:
#     options = F.get_options(field_id)
#     allowed = {o["value"] for o in options}

#     if isinstance(value, bool) and {"yes", "no"} <= allowed:
#         return ("yes" if value else "no"), []

#     spoken = str(value).strip().casefold()
#     for option in options:
#         if spoken in {option["value"].casefold(), option["en"].casefold(), option["kn"].casefold()}:
#             return option["value"], []
#     if {"yes", "no"} <= allowed:
#         if spoken in TRUE_WORDS:
#             return "yes", []
#         if spoken in FALSE_WORDS:
#             return "no", []

#     labels = ", ".join(o[lang] for o in options)
#     return None, [_issue("invalid_choice", lang, options=labels)]

def _v_choice(field_id: str, ftype: str, rules: dict, value: Any, lang: str) -> Result:
    options = F.get_options(field_id)
    allowed = {o["value"] for o in options}

    if isinstance(value, bool) and {"yes", "no"} <= allowed:
        return ("yes" if value else "no"), []

    spoken = str(value).strip().strip(_WORD_STRIP).casefold()
    for option in options:
        if spoken in {option["value"].casefold(), option["en"].casefold(), option["kn"].casefold()}:
            return option["value"], []

    # Yes/no questions: accept "ಹೌದು ಹೌದು", "yes yes", "ಹೌದು, ಸರಿ". A no-word wins,
    # so "ಸರಿ ಇಲ್ಲ" (not right) is a no.
    if {"yes", "no"} <= allowed:
        words = {w.strip(_WORD_STRIP) for w in spoken.split()}
        if words & FALSE_WORDS:
            return "no", []
        if words & TRUE_WORDS:
            return "yes", []

    labels = ", ".join(o[lang] for o in options)
    return None, [_issue("invalid_choice", lang, options=labels)]


def _v_checkbox(field_id: str, ftype: str, rules: dict, value: Any, lang: str) -> Result:
    if isinstance(value, bool):
        accepted = value
    else:
        spoken = str(value).strip().casefold()
        if spoken in TRUE_WORDS:
            accepted = True
        elif spoken in FALSE_WORDS:
            accepted = False
        else:
            return None, [_issue("invalid_yes_no", lang)]
    # Required declarations are only satisfied when ticked
    if F.get_field(field_id).get("required") and not accepted:
        return None, [_issue("must_accept", lang)]
    return accepted, []


VALIDATORS: dict[str, Callable[..., Result]] = {
    "text": _v_text,
    "textarea": _v_text,
    "phone": _v_phone,
    "email": _v_email,
    "pincode": _v_pincode,
    "pan": _v_pan,
    "aadhaar": _v_aadhaar,
    "date": _v_date,
    "year": _v_year,
    "number": _v_number,
    "currency": _v_number,
    "percentage": _v_number,
    "choice": _v_choice,
    "checkbox": _v_checkbox,
}


# ---------------------------------------------------------------------
# Public API: one field
# ---------------------------------------------------------------------
def validate_field(
    field_id: str, value: Any, values: dict[str, Any], language: str = "en"
) -> tuple[Any, list[FieldIssue]]:
    """Check one answer. Returns (clean_value, issues); no issues means valid.
    `values` is the current application, used to suggest the right field."""
    lang = _lang(language)
    if not F.field_exists(field_id):
        return None, [_issue("unknown_field", lang)]

    field = F.get_field(field_id)
    ftype = field["type"]
    rules = field.get("validation") or {}

    if isinstance(value, str):
        value = normalize_digits(value.strip())

    validator = VALIDATORS.get(ftype, _v_text)
    clean, issues = validator(field_id, ftype, rules, value, lang)

    if issues:
        # A value that fails may simply belong to another field
        wrong = _wrong_field_issue(field_id, ftype, value, values, lang)
        return None, [wrong] if wrong else issues

    if ftype in ("text", "textarea"):
        wrong = _wrong_field_issue(field_id, ftype, value, values, lang, strong_only=True)
        if wrong:
            return None, [wrong]
    return clean, []


# ---------------------------------------------------------------------
# Cross-field rules (ids and messages come from the schema)
# ---------------------------------------------------------------------
def _n(values: dict[str, Any], key: str) -> int | float | None:
    v = values.get(key)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _marks_not_above_max(v: dict) -> bool | None:
    a, b = _n(v, "marks_obtained"), _n(v, "max_marks")
    return None if a is None or b is None else a <= b


def _percentage_matches(v: dict) -> bool | None:
    a, b, p = _n(v, "marks_obtained"), _n(v, "max_marks"), _n(v, "percentage")
    if a is None or b is None or p is None or b == 0:
        return None
    return abs(p - a / b * 100) <= 0.05


def _loan_within_gap(v: dict) -> bool | None:
    loan, total, margin = (
        _n(v, "loan_amount_requested"), _n(v, "total_course_cost"), _n(v, "margin_money_amount"),
    )
    if loan is None or total is None or margin is None:
        return None
    return loan <= total - margin - (_n(v, "scholarship_amount") or 0)


def _course_after_passing(v: dict) -> bool | None:
    start, passed = _n(v, "course_start_year"), _n(v, "year_of_passing")
    return None if start is None or passed is None else start >= passed


def _passing_after_birth(v: dict) -> bool | None:
    passed, dob = _n(v, "year_of_passing"), v.get("date_of_birth")
    if passed is None or not isinstance(dob, str) or not re.match(r"^\d{4}-", dob):
        return None
    return passed - int(dob[:4]) >= 14


def _tenure_ok(v: dict) -> bool | None:
    tenure = _n(v, "repayment_tenure_years")
    return None if tenure is None else tenure >= 1


# True = fine, False = violated, None = not enough answers yet to decide
CROSS_CHECKS: dict[str, Callable[[dict], bool | None]] = {
    "marks_not_above_max": _marks_not_above_max,
    "percentage_matches_marks": _percentage_matches,
    "loan_within_funding_gap": _loan_within_gap,
    "course_starts_after_passing": _course_after_passing,
    "passing_year_after_birth": _passing_after_birth,
    "tenure_covers_reasonable_period": _tenure_ok,
}


@dataclass
class CrossViolation:
    rule_id: str
    fields: list[str]
    message: str


def find_cross_violations(
    values: dict[str, Any], language: str = "en", changed_field: str | None = None
) -> list[CrossViolation]:
    """Rules that are broken by `values`. With `changed_field`, only rules that
    involve that field are checked."""
    lang = _lang(language)
    violations: list[CrossViolation] = []
    for rule in F.load_schema().get("cross_field_rules", []):
        if changed_field and changed_field not in rule["fields"]:
            continue
        check = CROSS_CHECKS.get(rule["id"])
        if check is not None and check(values) is False:
            violations.append(
                CrossViolation(rule["id"], rule["fields"], rule["message"][lang])
            )
    return violations


def check_cross_rules(
    values: dict[str, Any], language: str = "en", changed_field: str | None = None
) -> list[FieldIssue]:
    """Same as find_cross_violations, as applicant-facing issues."""
    return [
        FieldIssue(code="cross_field", message=v.message, hint=None)
        for v in find_cross_violations(values, language, changed_field)
    ]


# ---------------------------------------------------------------------
# Public API: whole application (used by the readiness check in Phase 15)
# ---------------------------------------------------------------------
def validate_application(
    values: dict[str, Any], language: str = "en"
) -> tuple[list[str], dict[str, list[FieldIssue]], list[CrossViolation]]:
    """Returns (missing required field IDs, issues per field, cross-field
    violations) for the whole application."""
    lang = _lang(language)
    missing = [
        field_id
        for field_id in F.required_field_ids(values, include_calculated=True)
        if not F.is_answered(field_id, values.get(field_id))
    ]

    field_issues: dict[str, list[FieldIssue]] = {}
    for field_id in F.visible_field_ids(values):
        if field_id in values and F.is_answered(field_id, values[field_id]):
            _, issues = validate_field(field_id, values[field_id], values, lang)
            if issues:
                field_issues[field_id] = issues

    return missing, field_issues, find_cross_violations(values, lang)