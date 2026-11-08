"""Usage (from the project root):  python scripts\check_gemini.py"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings
from ai_engine.agent.llm_client import LLMError, generate_json, list_models

print("Configured model:", settings.LLM_MODEL)

try:
    flash = sorted(
        m["name"].removeprefix("models/") for m in list_models() if "flash" in m["name"].lower()
    )
    print("Flash models your key can use:")
    for name in flash:
        print("  ", name, "  <- configured" if name == settings.LLM_MODEL else "")
except LLMError as e:
    sys.exit(f"Could not list models: {e}")

if settings.LLM_MODEL not in flash:
    print("\nThe configured model is not in that list. Pick one above and set LLM_MODEL in backend/.env.")

started = time.perf_counter()
try:
    result = generate_json(
        'Reply with a JSON object only: {"fields": {"<field_id>": "<value>"}}.',
        'Field ids: full_name, mobile_number. The applicant said: "I am Lavanya and my number is nine eight seven six five four three two one zero".',
    )
except LLMError as e:
    sys.exit(f"\nGemini call failed: {e}")

print(f"\nGemini answered in {time.perf_counter() - started:.2f}s:")
print(result)