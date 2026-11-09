"""
Language handling for the voice layer (Kannada and English).

    detect_script("ನನ್ನ PAN ABCPE1234F")  -> "mixed"
    normalize_transcript("nine eight seven six five four")  -> "987654"
    parse_yes_no("ಸರಿ ಇಲ್ಲ")  -> False
    voice_error_message(error, "kn")  -> a Kannada sentence for the applicant

Speech recognition returns what was said; this module cleans it for the
validation engine without deciding anything about validity. It only rewrites
text that is clearly a digit sequence (4 or more spoken digits in a row), so
ordinary sentences are left alone.
"""

import re

from ai_engine.voice.gnani_client import (
    AUTH,
    BAD_REQUEST,
    CREDITS,
    NETWORK,
    RATE_LIMIT,
    TIMEOUT,
    UNAVAILABLE,
    GnaniError,
)
from shared.constants.languages import normalize_digits, normalize_language

_KANNADA = re.compile(r"[\u0c80-\u0cff]")
_LATIN = re.compile(r"[A-Za-z]")
_EDGE_PUNCTUATION = ".,;:!?\"'()[]"


def resolve_language(code: str | None) -> str:
    """'en' or 'kn' for any language code the app or Gnani may send."""
    return normalize_language(code or "en").value


def detect_script(text: str) -> str:
    """'kn' (Kannada letters only), 'en' (Latin only), 'mixed', or 'none'."""
    has_kannada = bool(_KANNADA.search(text))
    has_latin = bool(_LATIN.search(text))
    if has_kannada and has_latin:
        return "mixed"
    if has_kannada:
        return "kn"
    if has_latin:
        return "en"
    return "none"


# ---------------------------------------------------------------------
# Spoken digits -> digits
# ---------------------------------------------------------------------
DIGIT_WORDS: dict[str, str] = {
    # English
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    # Kannada script
    "ಸೊನ್ನೆ": "0", "ಒಂದು": "1", "ಎರಡು": "2", "ಮೂರು": "3", "ನಾಲ್ಕು": "4",
    "ಐದು": "5", "ಆರು": "6", "ಏಳು": "7", "ಎಂಟು": "8", "ಒಂಬತ್ತು": "9",
    # Kannada in Roman letters (when recognition is asked for English)
    "sonne": "0", "ondu": "1", "eradu": "2", "mooru": "3", "muru": "3",
    "naalku": "4", "aidu": "5", "aaru": "6", "elu": "7", "entu": "8",
    "ombattu": "9",
}
REPEAT_WORDS: dict[str, int] = {
    "double": 2, "triple": 3, "ಡಬಲ್": 2, "ಟ್ರಿಪಲ್": 3,
}
MIN_SPOKEN_DIGITS = 4  # shorter runs ("one two three") are left as words


def _clean_token(token: str) -> str:
    return token.strip(_EDGE_PUNCTUATION).casefold()


def _digits_for(tokens: list[str], index: int) -> tuple[str, int] | None:
    """Digits spoken at tokens[index], and how many tokens they use."""
    word = _clean_token(tokens[index])
    if word in DIGIT_WORDS:
        return DIGIT_WORDS[word], 1
    if re.fullmatch(r"[0-9]", word):
        return word, 1
    if word in REPEAT_WORDS and index + 1 < len(tokens):
        following = _clean_token(tokens[index + 1])
        digit = DIGIT_WORDS.get(following) or (following if re.fullmatch(r"[0-9]", following) else None)
        if digit:
            return digit * REPEAT_WORDS[word], 2
    return None


def normalize_transcript(text: str) -> str:
    """Clean a transcript for the validation engine:
    Kannada numerals become 0-9, and runs of 4+ spoken digits become digits
    ("ಒಂಬತ್ತು ಎಂಟು ಏಳು ಆರು" -> "9876"). Everything else is left as spoken."""
    tokens = normalize_digits(" ".join(text.split())).split(" ")
    if tokens == [""]:
        return ""

    output: list[str] = []
    i = 0
    while i < len(tokens):
        run_digits = ""
        run_tokens = 0
        j = i
        while j < len(tokens):
            found = _digits_for(tokens, j)
            if found is None:
                break
            run_digits += found[0]
            run_tokens += found[1]
            j += found[1]
        if len(run_digits) >= MIN_SPOKEN_DIGITS:
            output.append(run_digits)
            i += run_tokens
        else:
            output.append(tokens[i])
            i += 1
    return compact_spelled_id(" ".join(output))

# ---------------------------------------------------------------------
# Spelled-out IDs: "A P C P E 1234 F" -> "APCPE1234F"
# ---------------------------------------------------------------------
_SPELLED_PART = re.compile(r"^(?:[A-Za-z]|\d+)$")


def compact_spelled_id(text: str) -> str:
    """Join letters and digit groups that were spoken one by one into a single
    code. A run needs at least 3 pieces and 2 single letters, so ordinary
    sentences are left alone ("A P C P E 1234 F" joins; "I have 3 apples" does not)."""
    tokens = text.split(" ")
    output: list[str] = []
    i = 0
    while i < len(tokens):
        j = i
        while j < len(tokens) and _SPELLED_PART.match(tokens[j].strip(_EDGE_PUNCTUATION)):
            j += 1
        run = [t.strip(_EDGE_PUNCTUATION) for t in tokens[i:j]]
        if len(run) >= 3 and sum(1 for t in run if len(t) == 1 and t.isalpha()) >= 2:
            output.append("".join(run).upper())
            i = j
        else:
            output.append(tokens[i])
            i += 1
    return " ".join(output)


# Fields whose answer is Latin letters, not Kannada words. Recognising them in
# English mode stops names and addresses being turned into Kannada script.
SPOKEN_IN_ENGLISH_FIELDS = {"email", "pan"}


def stt_language_for_field(field_type: str | None, app_language: str) -> str:
    """The language to ask Gnani to listen for, given the field being answered."""
    if field_type in SPOKEN_IN_ENGLISH_FIELDS:
        return "en"
    return resolve_language(app_language)

# ---------------------------------------------------------------------
# Yes / no (for read-back confirmations)
# ---------------------------------------------------------------------
YES_WORDS = {
    "yes", "yeah", "yep", "yup", "correct", "right", "ok", "okay", "sure",
    "exactly", "haudu", "houdu", "sari", "sariyagide",
    "ಹೌದು", "ಸರಿ", "ಸರಿಯಾಗಿದೆ",
}
NO_WORDS = {
    "no", "nope", "not", "wrong", "incorrect", "illa", "beda", "tappu",
    "tappagide", "sariyilla",
    "ಇಲ್ಲ", "ಬೇಡ", "ತಪ್ಪು", "ತಪ್ಪಾಗಿದೆ", "ಸರಿಯಿಲ್ಲ",
}


def parse_yes_no(text: str) -> bool | None:
    """True for yes, False for no, None when it is neither or unclear.
    A no-word wins over a yes-word, so "ಸರಿ ಇಲ್ಲ" (not right) is False."""
    words = {_clean_token(t) for t in text.split()}
    if words & NO_WORDS:
        return False
    if words & YES_WORDS:
        return True
    return None


# ---------------------------------------------------------------------
# Fixed phrases the voice layer itself says
# ---------------------------------------------------------------------
MESSAGES: dict[str, dict[str, str]] = {
    "not_heard": {
        "en": "Sorry, I could not hear that. Please say it again.",
        "kn": "ಕ್ಷಮಿಸಿ, ನನಗೆ ಕೇಳಿಸಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಇನ್ನೊಮ್ಮೆ ಹೇಳಿ.",
    },
    "voice_busy": {
        "en": "The voice service is busy right now. Please try again in a moment, or type your answer.",
        "kn": "ಧ್ವನಿ ಸೇವೆ ಈಗ ಬ್ಯುಸಿಯಾಗಿದೆ. ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.",
    },
    "voice_unavailable": {
        "en": "Voice is not available right now. Please type your answer instead.",
        "kn": "ಧ್ವನಿ ಸೇವೆ ಈಗ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಟೈಪ್ ಮಾಡಿ ಉತ್ತರಿಸಿ.",
    },
    "audio_unsupported": {
        "en": "That recording could not be used. Please record again.",
        "kn": "ಈ ರೆಕಾರ್ಡಿಂಗ್ ಬಳಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೊಮ್ಮೆ ರೆಕಾರ್ಡ್ ಮಾಡಿ.",
    },
    "recording_too_long": {
        "en": "That recording is too long. Please speak for less than 30 seconds.",
        "kn": "ರೆಕಾರ್ಡಿಂಗ್ ತುಂಬಾ ಉದ್ದವಾಗಿದೆ. ದಯವಿಟ್ಟು 30 ಸೆಕೆಂಡ್‌ಗಿಂತ ಕಡಿಮೆ ಮಾತನಾಡಿ.",
    },
}


def message(key: str, language: str = "en") -> str:
    entry = MESSAGES[key]
    return entry.get(resolve_language(language)) or entry["en"]


def voice_error_message(error: GnaniError, language: str = "en") -> str:
    """What to tell the applicant when a Gnani call fails. Never exposes
    technical details; the applicant is always pointed to typing."""
    if error.kind == BAD_REQUEST:
        if error.code in ("EMPTY_AUDIO", "EMPTY_TEXT"):
            return message("not_heard", language)
        if error.code in ("MAX_AUDIO_DURATION_EXCEEDED", "AUDIO_TOO_LARGE"):
            return message("recording_too_long", language)
        return message("audio_unsupported", language)
    if error.kind in (RATE_LIMIT, TIMEOUT, NETWORK):
        return message("voice_busy", language)
    if error.kind in (AUTH, CREDITS, UNAVAILABLE):
        return message("voice_unavailable", language)
    return message("voice_unavailable", language)

# ---------------------------------------------------------------------
# Kannada script -> English letters (for names and places)
# ---------------------------------------------------------------------
_KN_VOWELS = {
    "ಅ": "a", "ಆ": "a", "ಇ": "i", "ಈ": "i", "ಉ": "u", "ಊ": "u", "ಋ": "ru",
    "ಎ": "e", "ಏ": "e", "ಐ": "ai", "ಒ": "o", "ಓ": "o", "ಔ": "au",
}
_KN_CONSONANTS = {
    "ಕ": "k", "ಖ": "kh", "ಗ": "g", "ಘ": "gh", "ಙ": "ng",
    "ಚ": "ch", "ಛ": "chh", "ಜ": "j", "ಝ": "jh", "ಞ": "ny",
    "ಟ": "t", "ಠ": "th", "ಡ": "d", "ಢ": "dh", "ಣ": "n",
    "ತ": "t", "ಥ": "th", "ದ": "d", "ಧ": "dh", "ನ": "n",
    "ಪ": "p", "ಫ": "ph", "ಬ": "b", "ಭ": "bh", "ಮ": "m",
    "ಯ": "y", "ರ": "r", "ಲ": "l", "ವ": "v", "ಶ": "sh", "ಷ": "sh",
    "ಸ": "s", "ಹ": "h", "ಳ": "l", "ೞ": "zh", "ಱ": "r",
}
_KN_MATRAS = {
    "ಾ": "a", "ಿ": "i", "ೀ": "i", "ು": "u", "ೂ": "u", "ೃ": "ru",
    "ೆ": "e", "ೇ": "e", "ೈ": "ai", "ೊ": "o", "ೋ": "o", "ೌ": "au",
}
_VIRAMA, _ANUSVARA, _VISARGA = "\u0ccd", "\u0c82", "\u0c83"
_IGNORED = {"\u200c", "\u200d"}  # zero-width joiners


def has_kannada(text: str) -> bool:
    return bool(_KANNADA.search(text))


def _romanize_word(word: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(word):
        ch = word[i]
        nxt = word[i + 1] if i + 1 < len(word) else ""
        if ch in _IGNORED:
            pass
        elif ch in _KN_CONSONANTS:
            out.append(_KN_CONSONANTS[ch])
            if nxt in _KN_MATRAS:
                out.append(_KN_MATRAS[nxt])
                i += 1
            elif nxt == _VIRAMA:
                i += 1  # vowel-less: the next consonant joins on
            else:
                out.append("a")  # inherent vowel
        elif ch in _KN_VOWELS:
            out.append(_KN_VOWELS[ch])
        elif ch == _ANUSVARA:
            following = _KN_CONSONANTS.get(nxt, "")
            out.append("m" if (not nxt or following[:1] in ("p", "b", "m")) else "n")
        elif ch == _VISARGA:
            out.append("h")
        else:
            out.append(ch)  # Latin letters, digits and punctuation pass through
        i += 1
    return "".join(out)


def romanize_if_kannada(text: str) -> str:
    """Kannada words become English letters ("ನಾಗೇಂದ್ರ" -> "Nagendra");
    words already in English are left as they are."""
    if not has_kannada(text):
        return text
    words = []
    for token in text.split(" "):
        if has_kannada(token):
            roman = _romanize_word(token)
            token = roman[:1].upper() + roman[1:]
        words.append(token)
    return " ".join(words)