"""Usage (from the project root):  python scripts\check_tts.py"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from ai_engine.voice.gnani_client import GnaniError
from ai_engine.voice.text_to_speech import spell_out, synthesize_speech

OUT = ROOT / "scripts" / "out"
OUT.mkdir(exist_ok=True)

TESTS = [
    ("kannada_greeting", "kn",
     "ನಮಸ್ಕಾರ, ನಾನು ಧ್ವನಿ. ನಿಮ್ಮ ಶಿಕ್ಷಣ ಸಾಲದ ಅರ್ಜಿಯನ್ನು ತುಂಬಲು ನಾನು ಸಹಾಯ ಮಾಡುತ್ತೇನೆ."),
    ("english_readback", "en",
     f"I heard your PAN as {spell_out('ABCPE1234F')} and your mobile number as "
     f"{spell_out('9876543210')}. Is that correct?"),
]

for name, language, text in TESTS:
    try:
        speech = synthesize_speech(text, language)
    except GnaniError as e:
        sys.exit(f"{name} failed: {e}")
    path = OUT / f"{name}.{speech.container}"
    path.write_bytes(speech.audio)
    print(f"{name}: {len(speech.audio)} bytes, {speech.latency_seconds}s, voice={speech.voice}, lang={speech.language}")
    os.startfile(path)  # Windows: opens in your default audio player