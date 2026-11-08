"""Usage (from the project root):  python scripts\check_stt.py path\to\clip.m4a [kn|en]"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from ai_engine.voice.gnani_client import GnaniError
from ai_engine.voice.speech_to_text import transcribe_audio

if len(sys.argv) < 2:
    sys.exit("Give the path to an audio file.")

path = Path(sys.argv[1])
language = sys.argv[2] if len(sys.argv) > 2 else "en"

try:
    result = transcribe_audio(path.read_bytes(), path.name, language)
except GnaniError as e:
    sys.exit(f"Failed: {e}")

print("text:      ", result.text or "(nothing heard)")
print("detected:  ", result.detected_language)
print("model:     ", result.model)
print("round trip:", result.latency_seconds, "s | gnani processing:", result.processing_seconds, "s")