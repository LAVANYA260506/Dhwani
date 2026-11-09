"""
Text-to-speech adapter (Gnani Timbre).

    speech = synthesize_speech("ನಮಸ್ಕಾರ", app_language="kn")
    speech.audio          # bytes, ready to play (mp3 by default)
    speech.content_type   # e.g. "audio/mpeg"

    spell_out("ABCPE1234F")  ->  "A B C P E 1 2 3 4 F"

Gnani mispronounces IDs and numbers sent as plain strings. Anything that must
be read character by character (phone, PAN, Aadhaar, PIN, register number)
goes through spell_out() first. Amounts and years can stay as they are
("Rs 1,00,000").

Failures raise GnaniError (see gnani_client.py).
"""

import logging
import re
from dataclasses import dataclass

from ai_engine.voice.gnani_client import BAD_REQUEST, GnaniError, get_gnani_client

logger = logging.getLogger("dhwani.voice")

TTS_PATH = "/api/v1/tts/inference"

# My own safety cap (not a Gnani limit): keeps spoken replies short and cheap.
MAX_TEXT_CHARS = 1000

CONTENT_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "raw": "application/octet-stream",
}

_KANNADA = re.compile(r"[\u0c80-\u0cff]")
_LATIN = re.compile(r"[A-Za-z]")


@dataclass
class Speech:
    audio: bytes
    content_type: str
    container: str
    voice: str
    language: str
    request_id: str
    latency_seconds: float


def spell_out(value: object) -> str:
    """Separate every character with a space so Gnani reads it one by one.
    Spaces, dashes and dots in the input are dropped first."""
    cleaned = re.sub(r"[\s\-.]", "", str(value))
    return " ".join(cleaned)


def clean_for_speech(text: str) -> str:
    """Remove markdown and decoration that would be read out or garbled."""
    text = re.sub(r"[`*_#>|~]", "", text)
    text = re.sub(r"^\s*[-\u2022]\s+", "", text, flags=re.MULTILINE)
    return " ".join(text.split())


def tts_language_param(app_language: str, text: str) -> str:
    """Language to tell Gnani. Kannada text that also contains English letters
    (a spelled-out PAN, a bank name) uses "auto", which Gnani recommends for
    mixed content."""
    if app_language == "kn":
        if _KANNADA.search(text) and _LATIN.search(text):
            return "auto"
        return "kn-IN"
    return "en-IN"


def _audio_config(container: str, sample_rate: int) -> dict:
    config: dict = {
        "sample_rate": sample_rate,
        "num_channels": 1,
        "sample_width": 2,
        "container": container,
    }
    if container in ("wav", "raw"):
        config["encoding"] = "linear_pcm"
    return config


def synthesize_speech(
    text: str,
    app_language: str = "en",
    *,
    speed: float | None = None,
    voice: str | None = None,
) -> Speech:
    """Turn text into spoken audio. `speed` is 0.85 (slow) to 1.15 (fast)."""
    from app.config import settings  # imported here to keep this module standalone

    text = clean_for_speech(text)
    if not text:
        raise GnaniError(BAD_REQUEST, "There is no text to speak.", code="EMPTY_TEXT")
    if len(text) > MAX_TEXT_CHARS:
        raise GnaniError(
            BAD_REQUEST,
            f"The reply is too long to speak ({len(text)} characters, limit {MAX_TEXT_CHARS}).",
            code="TEXT_TOO_LONG",
        )

    chosen_speed = settings.GNANI_TTS_SPEED if speed is None else speed
    chosen_speed = max(0.85, min(1.15, chosen_speed))
    chosen_voice = voice or settings.GNANI_TTS_VOICE
    container = settings.GNANI_TTS_CONTAINER
    language = tts_language_param(app_language, text)

    payload = {
        "text": text,
        "voice": chosen_voice,
        "model": settings.GNANI_TTS_MODEL,
        "language": language,
        "speed": chosen_speed,
        "audio_config": _audio_config(container, settings.GNANI_TTS_SAMPLE_RATE),
    }

    response = get_gnani_client().request("POST", TTS_PATH, json=payload)

    # A failure can come back as JSON; real audio never starts like that
    if "json" in response.content_type.lower() or not response.content:
        raise GnaniError(
            "unavailable", "The voice service did not return any audio.",
            request_id=response.request_id,
        )

    speech = Speech(
        audio=response.content,
        content_type=response.content_type or CONTENT_TYPES.get(container, "audio/mpeg"),
        container=container,
        voice=chosen_voice,
        language=language,
        request_id=response.request_id,
        latency_seconds=round(response.latency_seconds, 2),
    )
    logger.info(
        "tts ok: %d chars -> %d bytes, voice=%s, lang=%s, %.2fs",
        len(text), len(speech.audio), chosen_voice, language, speech.latency_seconds,
    )
    return speech