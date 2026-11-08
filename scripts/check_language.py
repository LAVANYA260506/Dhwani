"""Usage (from the project root):  python scripts\check_language.py"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from ai_engine.voice.gnani_client import GnaniError
from ai_engine.voice.language_handler import (
    detect_script, normalize_transcript, parse_yes_no, voice_error_message,
)

def check(label, got, expected):
    status = "ok  " if got == expected else "FAIL"
    print(f"{status} {label}: {got!r}" + ("" if got == expected else f"  (expected {expected!r})"))

check("script kn", detect_script("ನಮಸ್ಕಾರ"), "kn")
check("script mixed", detect_script("ನನ್ನ PAN ABCPE1234F"), "mixed")
check("english digits", normalize_transcript("my pin is five six zero zero zero one"), "my pin is 560001")
check("double", normalize_transcript("nine eight double seven six five"), "9877 65".replace(" ", ""))
check("kannada words", normalize_transcript("ಒಂಬತ್ತು ಎಂಟು ಏಳು ಆರು ಐದು ನಾಲ್ಕು"), "987654")
check("spaced digits", normalize_transcript("9 8 7 6 5 4 3 2 1 0"), "9876543210")
check("short run kept", normalize_transcript("I have one two apples"), "I have one two apples")
check("yes en", parse_yes_no("yes that is correct"), True)
check("yes kn", parse_yes_no("ಹೌದು ಸರಿ"), True)
check("no kn", parse_yes_no("ಇಲ್ಲ ತಪ್ಪು"), False)
check("not right kn", parse_yes_no("ಸರಿ ಇಲ್ಲ"), False)
check("unclear", parse_yes_no("maybe tomorrow"), None)
check("spelled PAN", normalize_transcript("My PAN is A P C P E 1234 F."), "My PAN is APCPE1234F")
check("article untouched", normalize_transcript("I have a car"), "I have a car")

print()
print(voice_error_message(GnaniError("rate_limit", "x"), "kn"))
print(voice_error_message(GnaniError("bad_request", "x", code="EMPTY_AUDIO"), "en"))