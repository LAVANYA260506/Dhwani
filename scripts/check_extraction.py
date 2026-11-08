"""Usage (from the project root):  python scripts\check_extraction.py"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from ai_engine.agent.extraction import extract, extract_by_rules

CASES = [
    ("en", "full_name", "My name is Lavanya, born 14 May 2003, PAN ABCPE1234F"),
    ("kn", "full_name", "ನನ್ನ ಹೆಸರು ಲಕ್ಷ್ಮಿ ಹೆಗಡೆ, ಮೊಬೈಲ್ ನಂಬರ್ 9876543210"),
    ("en", "full_name", "what does full name mean"),
    ("kn", "pan_number", "ಇದರ ಅರ್ಥ ಏನು?"),
    ("en", "study_country", "I am studying abroad in Germany"),
    ("en", "full_name", "Lavanya A"),
]

for language, current, text in CASES:
    print(f"\n[{language}] asking {current}: {text}")
    rules = extract_by_rules(text, language, current, {})
    print("  rules:", rules.intent, rules.fields, "| question:", rules.question_field)
    full = extract(text, language, current, {})
    print(f"  {full.source:5}:", full.intent, full.fields, "| question:", full.question_field,
          f"| llm_error: {full.llm_error}" if full.llm_error else "")