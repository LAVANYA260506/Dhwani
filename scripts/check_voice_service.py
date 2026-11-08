"""Usage (from the project root):  python scripts\check_voice_service.py"""

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.services.voice_service import VoiceService

kannada_application = SimpleNamespace(language="kn")
service = VoiceService()

print("Empty audio, Kannada session:")
outcome = service.transcribe(kannada_application, b"", "clip.m4a")
print("  ok:", outcome.ok, "| fallback:", outcome.fallback, "| kind:", outcome.error_kind)
print("  message:", outcome.message)

print("Unsupported format (webm), English session:")
outcome = service.transcribe(SimpleNamespace(language="en"), b"abc", "clip.webm")
print("  ok:", outcome.ok, "| fallback:", outcome.fallback)
print("  message:", outcome.message)

print("Empty text to speak:")
outcome = service.speak(kannada_application, "   ")
print("  ok:", outcome.ok, "| fallback:", outcome.fallback)
print("  message:", outcome.message)