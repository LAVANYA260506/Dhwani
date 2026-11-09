"""
Voice endpoints (all under /api). Both need the session token.

    POST /voice/transcribe   audio file in, recognised text out
    POST /voice/speak        text in, spoken audio out

How failures look, so the frontend can always react:

- transcribe always answers 200. "Nothing heard" and "voice is down" are normal
  outcomes, reported as ok=false with a `message` to show the applicant and a
  `fallback` ("retry" = speak again, "type" = switch to typing).
- speak answers with the audio on success. On failure it uses the standard
  error shape ({"error": {"code", "message", "details": {"fallback"}}}), so the
  frontend can show the message and carry on in text mode.
"""

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from pydantic import BaseModel, Field

from ai_engine.voice.speech_to_text import MAX_AUDIO_BYTES
from ai_engine.voice.text_to_speech import MAX_TEXT_CHARS
from app.api.deps import get_current_application
from app.core.exceptions import ExternalServiceError, FileTooLargeError
from app.models import Application
from app.services.voice_service import VoiceService

router = APIRouter(prefix="/voice", tags=["voice"])


class TranscribeResponse(BaseModel):
    ok: bool
    text: str = ""
    normalized: str = Field("", description="Cleaned for the validation engine")
    language: str = Field("en", description="Language Gnani was asked to listen for")
    detected_language: str | None = None
    latency_seconds: float | None = None
    truncated: bool = False
    message: str | None = Field(None, description="Show this to the applicant when not ok")
    fallback: str | None = Field(None, description="'retry' or 'type' when not ok")


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_CHARS)


def get_voice_service() -> VoiceService:
    return VoiceService()


@router.post("/transcribe", response_model=TranscribeResponse)
def transcribe(
    audio: UploadFile = File(..., description="Recording of up to 30 seconds (wav, mp3, m4a, ogg, flac, aac)"),
    field_id: str | None = Form(
        None, max_length=80,
        description="The field being answered. Emails and PAN are recognised in English.",
    ),
    application: Application = Depends(get_current_application),
    service: VoiceService = Depends(get_voice_service),
):
    # Read one byte past the limit so an oversized upload is caught without
    # loading all of it
    data = audio.file.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise FileTooLargeError("The recording is too large. Please keep it short.")

    outcome = service.transcribe(
        application, data, audio.filename or "audio.wav", field_id=field_id
    )
    return TranscribeResponse(
        ok=outcome.ok,
        text=outcome.text,
        normalized=outcome.normalized,
        language=outcome.language,
        detected_language=outcome.detected_language,
        latency_seconds=outcome.latency_seconds,
        truncated=outcome.truncated,
        message=outcome.message,
        fallback=outcome.fallback,
    )


@router.post("/speak")
def speak(
    payload: SpeakRequest,
    application: Application = Depends(get_current_application),
    service: VoiceService = Depends(get_voice_service),
):
    outcome = service.speak(application, payload.text)
    if not outcome.ok:
        raise ExternalServiceError(
            outcome.message, details={"fallback": outcome.fallback}
        )
    return Response(
        content=outcome.audio,
        media_type=outcome.content_type,
        headers={
            "Cache-Control": "no-store",
            "X-Voice-Latency": str(outcome.latency_seconds),
        },
    )