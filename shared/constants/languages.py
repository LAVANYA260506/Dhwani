"""
Language constants shared by the backend, AI engine and (mirrored in) the frontend.

Supported languages for the MVP: Kannada and English.
Numbers and dates are stored with English digits (0-9) regardless of the
spoken or displayed language.
"""

from __future__ import annotations

from enum import Enum


class Language(str, Enum):
    ENGLISH = "en"
    KANNADA = "kn"


DEFAULT_LANGUAGE = Language.ENGLISH
SUPPORTED_LANGUAGES: tuple[Language, ...] = (Language.ENGLISH, Language.KANNADA)

LANGUAGE_INFO: dict[Language, dict[str, str]] = {
    Language.ENGLISH: {
        "name": "English",
        "native_name": "English",
        # Locale code for browser speech / display formatting
        "locale": "en-IN",
        # Code sent to Gnani STT/TTS. Verify against Gnani's documentation
        # when credentials are available (Phase 8).
        "gnani_code": "en-IN",
    },
    Language.KANNADA: {
        "name": "Kannada",
        "native_name": "ಕನ್ನಡ",
        "locale": "kn-IN",
        "gnani_code": "kn-IN",
    },
}

# Accepted spellings when a language is given as free text or a locale code
_ALIASES: dict[str, Language] = {
    "en": Language.ENGLISH,
    "en-in": Language.ENGLISH,
    "en-us": Language.ENGLISH,
    "english": Language.ENGLISH,
    "kn": Language.KANNADA,
    "kn-in": Language.KANNADA,
    "kannada": Language.KANNADA,
    "ಕನ್ನಡ": Language.KANNADA,
}

# Kannada digits to English digits
_KANNADA_DIGITS = str.maketrans("೦೧೨೩೪೫೬೭೮೯", "0123456789")


def is_supported(code: str | None) -> bool:
    return normalize_language(code, fallback=None) is not None


def normalize_language(
    code: str | None, fallback: Language | None = DEFAULT_LANGUAGE
) -> Language | None:
    """Map 'kn', 'kn-IN', 'Kannada', 'ಕನ್ನಡ' etc. to a Language.
    Returns `fallback` (English by default) when the value is unknown."""
    if not code:
        return fallback
    return _ALIASES.get(code.strip().lower(), fallback)


def get_gnani_code(language: Language | str) -> str:
    lang = normalize_language(language if isinstance(language, str) else language.value)
    return LANGUAGE_INFO[lang]["gnani_code"]


def get_native_name(language: Language | str) -> str:
    lang = normalize_language(language if isinstance(language, str) else language.value)
    return LANGUAGE_INFO[lang]["native_name"]


def normalize_digits(text: str) -> str:
    """Convert Kannada digits (೧೨೩) to English digits (123) so that numbers
    and dates are always stored in one format."""
    return text.translate(_KANNADA_DIGITS)