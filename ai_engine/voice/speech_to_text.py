"""
Speech-to-text adapter (Gnani Prisma).

    result = transcribe_audio(audio_bytes, "clip.m4a", app_language="kn")
    result.text        # what was said ("" if nothing was heard)
    result.empty       # True when there was no speech (not an error)

- Checks the audio before spending a credit (empty, too big, unsupported type).
- For Kannada it asks Gnani to listen for Kannada and English together, so an
  English word, a PAN or a phone number inside a Kannada sentence is not lost.
- Numbers come back as digits (format=transcribe).
- Gnani's REST endpoint takes clips of up to 30 seconds. Longer audio is
  rejected by Gnani with MAX_AUDIO_DURATION_EXCEEDED.

Failures raise GnaniError (see gnani_client.py); the caller decides what to
tell the applicant (fallback behaviour is added in step 8H).
"""

import logging
from dataclasses import dataclass
from pathlib import PurePath

from ai_engine.voice.gnani_client import BAD_REQUEST, GnaniError, get_gnani_client

logger = logging.getLogger("dhwani.voice")

MAX_AUDIO_BYTES = 8 * 1024 * 1024  # a 30 second clip is far smaller than this

# Formats Gnani accepts, by file extension
AUDIO_TYPES = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".m4a": "audio/mp4",
}

STT_PATH = "/stt/v3"


@dataclass
class Transcription:
    text: str
    requested_languages: str          # what we asked Gnani to listen for
    model: str
    request_id: str
    latency_seconds: float            # our round trip, including upload
    processing_seconds: float | None  # Gnani's own processing time
    detected_language: str | None = None  # prisma-v3.0 only
    truncated: bool = False           # True if Gnani cut the transcript short

    @property
    def empty(self) -> bool:
        return not self.text.strip()


def stt_language_param(app_language: str, model: str) -> str:
    """The `language_code` to send for the applicant's language.

    prisma-v3.0 takes a list, so Kannada speech may contain English words.
    prisma-v2.5 accepts exactly one language.
    "auto" lets prisma-v3.0 identify the language itself.
    """
    is_v3 = model.startswith("prisma-v3")
    if app_language == "auto" and is_v3:
        return "indic-auto"
    if app_language == "kn":
        return "kn-IN,en-IN" if is_v3 else "kn-IN"
    return "en-IN"


def _check_audio(audio: bytes, filename: str) -> tuple[str, str]:
    """Return (filename, content_type) or raise a bad-request GnaniError."""
    if not audio:
        raise GnaniError(BAD_REQUEST, "No audio was received.", code="EMPTY_AUDIO")
    if len(audio) > MAX_AUDIO_BYTES:
        raise GnaniError(
            BAD_REQUEST, "The recording is too large. Please keep it short.",
            code="AUDIO_TOO_LARGE",
        )

    extension = PurePath(filename or "").suffix.lower()
    content_type = AUDIO_TYPES.get(extension)
    if content_type is None:
        supported = ", ".join(sorted(AUDIO_TYPES))
        raise GnaniError(
            BAD_REQUEST,
            f"This audio format is not supported. Use one of: {supported}.",
            code="UNSUPPORTED_AUDIO_FORMAT",
        )
    return filename, content_type


def transcribe_audio(
    audio: bytes,
    filename: str,
    app_language: str = "en",
    *,
    keyterms: list[str] | None = None,
    topic: str | None = None,
) -> Transcription:
    """Turn a short audio clip into text.

    `keyterms` and `topic` are optional hints (prisma-v3.0 only). Gnani warns
    that hints can lower accuracy, so they are off by default; compare with
    and without in the voice tests (step 8F).
    """
    from app.config import settings  # imported here to keep this module standalone

    filename, content_type = _check_audio(audio, filename)
    model = settings.GNANI_STT_MODEL
    language_param = stt_language_param(app_language, model)

    data: dict[str, str] = {
        "language_code": language_param,
        "format": settings.GNANI_STT_FORMAT,
    }
    if model != "prisma-v2.5":  # v2.5 is Gnani's default: leave `model` out
        data["model"] = model
    if model.startswith("prisma-v3"):
        if keyterms:
            import json

            data["keyterms"] = json.dumps(keyterms, ensure_ascii=False)
        if topic:
            data["topic"] = topic

    response = get_gnani_client().request(
        "POST",
        STT_PATH,
        data=data,
        files={"audio_file": (filename, audio, content_type)},
    )
    body = response.json()

    transcript = body.get("transcript", "")
    if not isinstance(transcript, str):
        raise GnaniError(
            "unavailable", "The voice service sent an unexpected transcript.",
            request_id=response.request_id,
        )

    result = Transcription(
        text=transcript.strip(),
        requested_languages=language_param,
        model=body.get("model") or model,
        request_id=body.get("request_id") or response.request_id,
        latency_seconds=round(response.latency_seconds, 2),
        processing_seconds=body.get("processing_time"),
        detected_language=body.get("detected_language_code"),
        truncated=bool(body.get("truncated", False)),
    )
    logger.info(
        "stt ok: %d chars, lang=%s, %.2fs, empty=%s",
        len(result.text), result.detected_language, result.latency_seconds, result.empty,
    )
    return result