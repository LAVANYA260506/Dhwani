"""Usage (server running; from the project root):  python scripts\check_voice_api.py"""

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://localhost:8000/api"
CLIP = ROOT / "scripts" / "out" / "kannada_greeting.mp3"

if not CLIP.exists():
    sys.exit("Run scripts\\check_tts.py first: it creates the test clip.")

created = requests.post(f"{BASE}/applications", json={"language": "kn", "consent_given": True}).json()
headers = {"Authorization": f"Bearer {created['session_token']}"}

print("1. Transcribe (Kannada session, name field):")
with CLIP.open("rb") as f:
    r = requests.post(
        f"{BASE}/voice/transcribe", headers=headers,
        files={"audio": (CLIP.name, f, "audio/mpeg")},
        data={"field_id": "full_name"},
    )
print("  ", r.status_code, r.json())

print("2. Transcribe with no auth (expect 401):")
with CLIP.open("rb") as f:
    r = requests.post(f"{BASE}/voice/transcribe", files={"audio": (CLIP.name, f, "audio/mpeg")})
print("  ", r.status_code, r.json())

print("3. Speak:")
r = requests.post(f"{BASE}/voice/speak", headers=headers, json={"text": "ನಿಮ್ಮ ಹೆಸರು ಏನು?"})
print("  ", r.status_code, r.headers.get("Content-Type"), len(r.content), "bytes",
      "| latency", r.headers.get("X-Voice-Latency"))
out = ROOT / "scripts" / "out" / "api_speak.mp3"
if r.ok:
    out.write_bytes(r.content)
    print("   saved:", out)