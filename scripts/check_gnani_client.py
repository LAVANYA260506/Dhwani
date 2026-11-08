import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_engine.voice.gnani_client import GnaniClient, GnaniError

client = GnaniClient("invalid-key-for-connection-test", max_retries=0)
try:
    client.request(
        "POST",
        "/api/v1/tts/inference",
        json={"text": "test", "model": "timbre-v3.0", "voice": "Lakshmi", "language": "kn-IN"},
    )
    print("Unexpected: the fake key was accepted.")
except GnaniError as e:
    print("kind:", e.kind, "| status:", e.status_code, "| code:", e.code)
    print("message:", e.message)