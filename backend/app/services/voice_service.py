"""
Voice service: speech-to-text and text-to-speech for one application.

    outcome = VoiceService().transcribe(application, audio, "clip.wav", field_id="pan_number")
    outcome.ok / outcome.normalized / outcome.message / outcome.fallback

Both methods return an outcome instead of raising when Gnani fails, so the API
can always reply with something the applicant can act on:

    fallback = "retry"  ->  try speaking again (nothing heard, busy, bad audio)
    fallback = "type"   ->  voice is down, switch to typing

The recognition language depends on the field being answered: emails and PAN
numbers are recognised in English even in a Kannada session.
"""

import threading
from dataclasses import dataclass

from ai_engine.voice import language_handler as lang
from ai_engine.voice.gnani_client import (
    AUTH,
    BAD_REQUEST,
    CREDITS,
    UNAVAILABLE,
    GnaniError,
)
from ai_engine.voice.speech_to_text import transcribe_audio
from ai_engine.voice.text_to_speech import synthesize_speech
from app.models import Application
from shared.constants import fields as F

# Some Gnani accounts allow one active request at a time. Voice calls are
# short, so taking turns is cheap and avoids 429 errors during a demo.
_gnani_lock = threading.Lock()

# Errors where retrying will not help: send the applicant to typing
_TYPE_INSTEAD = {AUTH, CREDITS, UNAVAILABLE}


@dataclass
class TranscribeOutcome:
    ok: bool
    text: str = ""                        # as recognised
    normalized: str = ""                  # cleaned for the validation engine
    language: str = "en"                  # language we asked Gnani to listen for
    detected_language: str | None = None
    latency_seconds: float | None = None
    truncated: bool = False               # Gnani cut the transcript short
    message: str | None = None            # for the applicant, when not ok
    fallback: str | None = None           # "retry" or "type"
    error_kind: str | None = None


@dataclass
class SpeakOutcome:
    ok: bool
    audio: bytes = b""
    content_type: str = ""
    container: str = ""
    voice: str = ""
    language: str = "en"
    latency_seconds: float | None = None
    message: str | None = None
    fallback: str | None = None
    error_kind: str | None = None


def _fallback_for(error: GnaniError) -> str:
    return "type" if error.kind in _TYPE_INSTEAD else "retry"


def _field_type(field_id: str | None) -> str | None:
    if field_id and F.field_exists(field_id):
        return F.get_field(field_id)["type"]
    return None


class VoiceService:
    def transcribe(
        self,
        application: Application,
        audio: bytes,
        filename: str,
        field_id: str | None = None,
    ) -> TranscribeOutcome:
        """Recognise one spoken answer. `field_id` is the field being asked
        about; it only affects which language Gnani listens for."""
        app_language = lang.resolve_language(application.language)
        listen_language = lang.stt_language_for_field(_field_type(field_id), app_language)

        try:
            with _gnani_lock:
                result = transcribe_audio(audio, filename, listen_language)
        except GnaniError as error:
            return TranscribeOutcome(
                ok=False,
                language=listen_language,
                message=lang.voice_error_message(error, app_language),
                fallback=_fallback_for(error),
                error_kind=error.kind,
            )

        if result.empty:
            # Silence or unintelligible audio is not an error: ask again
            return TranscribeOutcome(
                ok=False,
                language=listen_language,
                latency_seconds=result.latency_seconds,
                message=lang.message("not_heard", app_language),
                fallback="retry",
                error_kind=BAD_REQUEST,
            )

        return TranscribeOutcome(
            ok=True,
            text=result.text,
            normalized=lang.normalize_transcript(result.text),
            language=listen_language,
            detected_language=result.detected_language,
            latency_seconds=result.latency_seconds,
            truncated=result.truncated,
        )

    def speak(self, application: Application, text: str) -> SpeakOutcome:
        """Turn the assistant's reply into audio in the applicant's language."""
        app_language = lang.resolve_language(application.language)
        try:
            with _gnani_lock:
                speech = synthesize_speech(text, app_language)
        except GnaniError as error:
            return SpeakOutcome(
                ok=False,
                language=app_language,
                message=lang.voice_error_message(error, app_language),
                fallback=_fallback_for(error),
                error_kind=error.kind,
            )

        return SpeakOutcome(
            ok=True,
            audio=speech.audio,
            content_type=speech.content_type,
            container=speech.container,
            voice=speech.voice,
            language=speech.language,
            latency_seconds=speech.latency_seconds,
        )