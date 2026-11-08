"""
Voice measurements: recognition accuracy and latency (Phase 8, steps F and G).

    python scripts\measure_voice.py                  run all cases
    python scripts\measure_voice.py --list           show the cases and what to say
    python scripts\measure_voice.py --only kn_phone,en_pan

For each case the audio comes from a real recording if scripts\real_clips\<id>.<ext>
exists (m4a, wav, mp3, ogg, flac, aac); otherwise Gnani speaks the sentence.
The audio is transcribed, cleaned for the validation engine, and checked for the
expected value. Results are printed and saved to scripts\out\voice_measurements.csv.
"""

import argparse
import csv
import re
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from ai_engine.voice.gnani_client import GnaniError
from ai_engine.voice.language_handler import normalize_transcript
from ai_engine.voice.speech_to_text import AUDIO_TYPES, transcribe_audio
from ai_engine.voice.text_to_speech import spell_out, synthesize_speech

CLIPS = ROOT / "scripts" / "real_clips"
OUT = ROOT / "scripts" / "out"


@dataclass
class Case:
    id: str
    language: str          # "en" or "kn": the applicant's language
    category: str          # name / number / id / date / mixed
    say: str               # what a person should say (for real recordings)
    tts_text: str          # what Gnani speaks in synthetic mode
    expected: list[str]    # any of these in the transcript counts as correct
    stt_language: str | None = None  # override the recognition language for this case

CASES = [
    Case("en_name", "en", "name", "My name is Lavanya Hegde.",
         "My name is Lavanya Hegde.", ["Lavanya Hegde"]),
    Case("kn_name", "kn", "name", "ನನ್ನ ಹೆಸರು ಲಕ್ಷ್ಮಿ ಹೆಗಡೆ.",
         "ನನ್ನ ಹೆಸರು ಲಕ್ಷ್ಮಿ ಹೆಗಡೆ.", ["ಲಕ್ಷ್ಮಿ ಹೆಗಡೆ", "Lakshmi Hegde"]),
    Case("en_phone", "en", "number", "My mobile number is 9 8 7 6 5 4 3 2 1 0.",
         "My mobile number is " + spell_out("9876543210"), ["9876543210"]),
    Case("kn_phone", "kn", "number", "ನನ್ನ ಮೊಬೈಲ್ ಸಂಖ್ಯೆ 9 8 7 6 5 4 3 2 1 0.",
         "ನನ್ನ ಮೊಬೈಲ್ ಸಂಖ್ಯೆ " + spell_out("9876543210"), ["9876543210"]),
    Case("en_pan", "en", "id", "My PAN is A B C P E 1 2 3 4 F.",
         "My PAN is " + spell_out("ABCPE1234F"), ["ABCPE1234F"]),
    Case("en_aadhaar", "en", "id", "My Aadhaar number is 2 3 4 5 6 7 8 9 0 1 2 3.",
         "My Aadhaar number is " + spell_out("234567890123"), ["234567890123"]),
    Case("kn_pincode", "kn", "number", "ನನ್ನ ಪಿನ್ ಕೋಡ್ 5 6 0 0 0 1.",
         "ನನ್ನ ಪಿನ್ ಕೋಡ್ " + spell_out("560001"), ["560001"]),
    Case("en_dob", "en", "date", "My date of birth is 14 May 2003.",
         "My date of birth is 14 May 2003.",
         ["14 May 2003", "14th May 2003", "14-05-2003", "14/05/2003", "14.05.2003"]),
    Case("en_loan", "en", "number", "I need a loan of 5 lakh rupees.",
         "I need a loan of 5 lakh rupees.", ["500000", "5,00,000", "5lakh"]),
    Case("kn_mixed_email", "kn", "mixed", "ನನ್ನ ಇಮೇಲ್ lavanya at gmail dot com.",
        "ನನ್ನ ಇಮೇಲ್ lavanya at gmail dot com.",
        ["lavanya@gmail.com", "lavanya at gmail dot com", "lavanyaatgmaildotcom"],
        stt_language="en"),
]


def compact(text: str) -> str:
    return re.sub(r"[\s,\-\u20b9.]", "", text).casefold()


def is_correct(transcript: str, expected: list[str]) -> bool:
    heard = compact(normalize_transcript(transcript))
    return any(compact(option) in heard for option in expected)


def find_real_clip(case_id: str) -> Path | None:
    for extension in AUDIO_TYPES:
        candidate = CLIPS / f"{case_id}{extension}"
        if candidate.exists():
            return candidate
    return None


def run_case(case: Case) -> dict:
    row = {
        "case": case.id, "language": case.language, "category": case.category,
        "source": "", "correct": False, "heard": "", "tts_s": "", "stt_s": "",
        "stt_processing_s": "", "error": "",
    }
    try:
        clip = find_real_clip(case.id)
        if clip is not None:
            row["source"] = "real"
            audio, filename = clip.read_bytes(), clip.name
        else:
            row["source"] = "synthetic"
            speech = synthesize_speech(case.tts_text, case.language)
            row["tts_s"] = speech.latency_seconds
            audio, filename = speech.audio, f"{case.id}.{speech.container}"
            time.sleep(0.3)  # some accounts allow one active request at a time

        result = transcribe_audio(audio, filename, case.stt_language or case.language)
        row["heard"] = result.text
        row["stt_s"] = result.latency_seconds
        row["stt_processing_s"] = result.processing_seconds or ""
        row["correct"] = is_correct(result.text, case.expected)
    except GnaniError as error:
        row["error"] = f"{error.kind}/{error.code or error.status_code}"
    time.sleep(0.3)
    return row


def summarize(rows: list[dict]) -> None:
    done = [r for r in rows if not r["error"]]
    print()
    if not done:
        print("No case completed. Check the errors above.")
        return

    correct = sum(1 for r in done if r["correct"])
    print(f"Recognition: {correct}/{len(done)} correct ({correct / len(done):.0%})")
    for source in ("real", "synthetic"):
        subset = [r for r in done if r["source"] == source]
        if subset:
            ok = sum(1 for r in subset if r["correct"])
            print(f"  {source:9}: {ok}/{len(subset)}")
    for category in sorted({r["category"] for r in done}):
        subset = [r for r in done if r["category"] == category]
        ok = sum(1 for r in subset if r["correct"])
        print(f"  {category:9}: {ok}/{len(subset)}")

    for label, key in (("Speech to text", "stt_s"), ("Text to speech", "tts_s")):
        values = [r[key] for r in done if r[key] != ""]
        if values:
            print(f"{label}: median {statistics.median(values):.2f}s, slowest {max(values):.2f}s")
    failed = [r for r in rows if r["error"]]
    if failed:
        print(f"Errors: {len(failed)} (" + ", ".join(f"{r['case']}: {r['error']}" for r in failed) + ")")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="show the cases and exit")
    parser.add_argument("--only", help="comma-separated case IDs to run")
    args = parser.parse_args()

    if args.list:
        print(f"Save real recordings in: {CLIPS}\\<case_id>.m4a\n")
        for case in CASES:
            have = "recorded" if find_real_clip(case.id) else "-"
            print(f"{case.id:16} [{have:8}] say: {case.say}")
        return

    selected = CASES
    if args.only:
        wanted = {c.strip() for c in args.only.split(",")}
        selected = [c for c in CASES if c.id in wanted]
        if not selected:
            sys.exit("No matching case IDs. Use --list to see them.")

    OUT.mkdir(exist_ok=True)
    rows = []
    for case in selected:
        row = run_case(case)
        rows.append(row)
        mark = "ERROR" if row["error"] else ("ok   " if row["correct"] else "WRONG")
        timing = f"stt {row['stt_s']}s" if row["stt_s"] != "" else ""
        print(f"{mark} {case.id:16} {row['source']:9} {timing:10} heard: {row['heard'] or row['error']}")

    summarize(rows)

    path = OUT / "voice_measurements.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: opens correctly in Excel
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()