"""
Verified loan information and a basic criteria check.

    answer("documents", values, "kn")          fixed text about a topic
    answer("eligibility_check", values, "en")  the applicant's answers vs the published criteria
    detect_topic("am I eligible?")             keyword match, used when the model is unavailable

The facts are the same as the Education Loan page. Nothing here is generated
by a model, and nothing here decides anything: the criteria check only
compares the applicant's answers with the criteria shown on the website, and
says so. Interest rates, fees and approval chances are deliberately NOT
answered (topic "unknown"), so the assistant can never invent them.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

TOPIC_IDS = {
    "eligibility_check", "eligibility_criteria", "documents", "loan_amount",
    "repayment", "margin_money", "collateral", "co_applicant", "process", "unknown",
}

TOPICS: dict[str, dict[str, str]] = {
    "eligibility_criteria": {
        "en": (
            "To apply you should be an Indian student with a confirmed or awaited admission to a "
            "recognised course, aged 16 to 45, with a parent, guardian or other co-applicant who has "
            "a regular income. Undergraduate, postgraduate, diploma and PhD courses are covered. "
            "Ask me 'am I eligible?' and I will compare your answers with these points."
        ),
        "kn": (
            "ಅರ್ಜಿ ಸಲ್ಲಿಸಲು ನೀವು ಮಾನ್ಯತೆ ಪಡೆದ ಕೋರ್ಸ್‌ಗೆ ಖಚಿತ ಅಥವಾ ನಿರೀಕ್ಷಿತ ಪ್ರವೇಶ ಹೊಂದಿರುವ, "
            "16 ರಿಂದ 45 ವರ್ಷದ ಭಾರತೀಯ ವಿದ್ಯಾರ್ಥಿಯಾಗಿರಬೇಕು, ಮತ್ತು ನಿಯಮಿತ ಆದಾಯವಿರುವ ಪೋಷಕರು, ಪಾಲಕರು "
            "ಅಥವಾ ಸಹ-ಅರ್ಜಿದಾರರು ಇರಬೇಕು. ಪದವಿ, ಸ್ನಾತಕೋತ್ತರ, ಡಿಪ್ಲೊಮಾ ಮತ್ತು ಪಿಎಚ್‌ಡಿ ಕೋರ್ಸ್‌ಗಳು "
            "ಒಳಗೊಂಡಿವೆ. 'ನಾನು ಅರ್ಹತೆ ಹೊಂದಿದ್ದೇನೆಯೇ?' ಎಂದು ಕೇಳಿ, ನಿಮ್ಮ ಉತ್ತರಗಳನ್ನು ಇವುಗಳೊಂದಿಗೆ ಹೋಲಿಸುತ್ತೇನೆ."
        ),
    },
    "documents": {
        "en": (
            "You will need your Aadhaar number, your PAN if you have one, the marks card of your last "
            "qualifying exam, the admission letter and fee structure, and your co-applicant's PAN, "
            "income and existing EMI details."
        ),
        "kn": (
            "ನಿಮಗೆ ಆಧಾರ್ ಸಂಖ್ಯೆ, ಪ್ಯಾನ್ (ಇದ್ದರೆ), ನಿಮ್ಮ ಕೊನೆಯ ಅರ್ಹತಾ ಪರೀಕ್ಷೆಯ ಅಂಕಪಟ್ಟಿ, ಪ್ರವೇಶ ಪತ್ರ ಮತ್ತು "
            "ಶುಲ್ಕ ವಿವರ, ಹಾಗೂ ಸಹ-ಅರ್ಜಿದಾರರ ಪ್ಯಾನ್, ಆದಾಯ ಮತ್ತು ಈಗಿರುವ ಇಎಂಐ ವಿವರಗಳು ಬೇಕಾಗುತ್ತವೆ."
        ),
    },
    "loan_amount": {
        "en": (
            "You can request between 10,000 rupees and 1.5 crore rupees. The loan cannot be more than "
            "the course cost minus your margin money and any scholarship."
        ),
        "kn": (
            "ನೀವು 10,000 ರೂಪಾಯಿಯಿಂದ 1.5 ಕೋಟಿ ರೂಪಾಯಿಯವರೆಗೆ ಸಾಲ ಕೇಳಬಹುದು. ಸಾಲವು ಕೋರ್ಸ್ ವೆಚ್ಚದಿಂದ ನಿಮ್ಮ "
            "ಮಾರ್ಜಿನ್ ಹಣ ಮತ್ತು ವಿದ್ಯಾರ್ಥಿವೇತನವನ್ನು ಕಳೆದ ಮೊತ್ತಕ್ಕಿಂತ ಹೆಚ್ಚಿರಬಾರದು."
        ),
    },
    "repayment": {
        "en": (
            "Repayment can be spread over 1 to 15 years. It begins after your course ends plus the "
            "moratorium period."
        ),
        "kn": (
            "ಮರುಪಾವತಿಯನ್ನು 1 ರಿಂದ 15 ವರ್ಷಗಳಲ್ಲಿ ಹರಡಬಹುದು. ನಿಮ್ಮ ಕೋರ್ಸ್ ಮುಗಿದು ನಿಗದಿತ ಅವಧಿಯ ನಂತರ "
            "ಮರುಪಾವತಿ ಆರಂಭವಾಗುತ್ತದೆ."
        ),
    },
    "margin_money": {
        "en": (
            "Margin money is the part of the course cost that you or your family pay yourselves; the "
            "loan covers the rest. You enter the amount and where it comes from in the loan section."
        ),
        "kn": (
            "ಮಾರ್ಜಿನ್ ಹಣ ಎಂದರೆ ಕೋರ್ಸ್ ವೆಚ್ಚದಲ್ಲಿ ನೀವು ಅಥವಾ ನಿಮ್ಮ ಕುಟುಂಬ ಸ್ವತಃ ಭರಿಸುವ ಭಾಗ; ಉಳಿದುದನ್ನು ಸಾಲ "
            "ಭರಿಸುತ್ತದೆ. ಸಾಲದ ವಿಭಾಗದಲ್ಲಿ ಮೊತ್ತ ಮತ್ತು ಅದರ ಮೂಲವನ್ನು ನಮೂದಿಸಿ."
        ),
    },
    "collateral": {
        "en": (
            "The form asks whether you are offering collateral, such as property, a fixed deposit or an "
            "insurance policy. Whether collateral is required is decided by the bank."
        ),
        "kn": (
            "ನೀವು ಆಸ್ತಿ, ಸ್ಥಿರ ಠೇವಣಿ ಅಥವಾ ವಿಮಾ ಪಾಲಿಸಿಯಂತಹ ಭದ್ರತೆಯನ್ನು ನೀಡುತ್ತೀರಾ ಎಂದು ಅರ್ಜಿ ಕೇಳುತ್ತದೆ. "
            "ಭದ್ರತೆ ಅಗತ್ಯವೇ ಎಂಬುದನ್ನು ಬ್ಯಾಂಕ್ ನಿರ್ಧರಿಸುತ್ತದೆ."
        ),
    },
    "co_applicant": {
        "en": (
            "A co-applicant shares responsibility for repaying the loan. This form asks for their "
            "relationship to you (father, mother, guardian, spouse, brother or sister, or other), date "
            "of birth, PAN, mobile number, occupation, employer, annual income and existing EMIs. The "
            "co-applicant must be an adult aged 18 to 80 with a regular income, so a child cannot be a "
            "co-applicant. Whether a particular person is accepted is the bank's decision."
        ),
        "kn": (
            "ಸಹ-ಅರ್ಜಿದಾರರು ಸಾಲ ಮರುಪಾವತಿಯ ಜವಾಬ್ದಾರಿಯನ್ನು ಹಂಚಿಕೊಳ್ಳುವವರು. ಈ ಅರ್ಜಿಯಲ್ಲಿ ಅವರ ಸಂಬಂಧ (ತಂದೆ, "
            "ತಾಯಿ, ಪಾಲಕರು, ಸಂಗಾತಿ, ಸಹೋದರ ಅಥವಾ ಸಹೋದರಿ, ಇತರೆ), ಹುಟ್ಟಿದ ದಿನಾಂಕ, ಪ್ಯಾನ್, ಮೊಬೈಲ್ ಸಂಖ್ಯೆ, "
            "ವೃತ್ತಿ, ಉದ್ಯೋಗದಾತ, ವಾರ್ಷಿಕ ಆದಾಯ ಮತ್ತು ಈಗಿರುವ ಇಎಂಐ ಕೇಳಲಾಗುತ್ತದೆ. ಸಹ-ಅರ್ಜಿದಾರರು ನಿಯಮಿತ "
            "ಆದಾಯವಿರುವ 18 ರಿಂದ 80 ವರ್ಷದ ವಯಸ್ಕರಾಗಿರಬೇಕು, ಆದ್ದರಿಂದ ಮಗು ಸಹ-ಅರ್ಜಿದಾರರಾಗಲು ಸಾಧ್ಯವಿಲ್ಲ. "
            "ಯಾವುದೇ ನಿರ್ದಿಷ್ಟ ವ್ಯಕ್ತಿಯನ್ನು ಒಪ್ಪಬೇಕೇ ಎಂಬುದನ್ನು ಬ್ಯಾಂಕ್ ನಿರ್ಧರಿಸುತ್ತದೆ."
        ),
    },
    "process": {
        "en": (
            "Choose your language, answer by voice or typing, and I will read back important details "
            "before saving them. Then you review the whole application and confirm to submit. This is "
            "a prototype: nothing is sent to a real bank."
        ),
        "kn": (
            "ನಿಮ್ಮ ಭಾಷೆಯನ್ನು ಆರಿಸಿ, ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ ಉತ್ತರಿಸಿ; ಮುಖ್ಯ ವಿವರಗಳನ್ನು ಉಳಿಸುವ ಮೊದಲು ನಾನು ಓದಿ "
            "ಹೇಳುತ್ತೇನೆ. ನಂತರ ಸಂಪೂರ್ಣ ಅರ್ಜಿಯನ್ನು ಪರಿಶೀಲಿಸಿ ಮತ್ತು ಸಲ್ಲಿಸಲು ಖಚಿತಪಡಿಸಿ. ಇದು ಮಾದರಿ ಮಾತ್ರ: "
            "ನಿಜವಾದ ಬ್ಯಾಂಕ್‌ಗೆ ಏನೂ ಕಳುಹಿಸಲಾಗುವುದಿಲ್ಲ."
        ),
    },
    "unknown": {
        "en": (
            "I don't have verified information about that in this demo, such as interest rates, fees or "
            "your chances of approval, and I can't predict them. Please contact the EduVest helpline "
            "shown on the website."
        ),
        "kn": (
            "ಬಡ್ಡಿ ದರ, ಶುಲ್ಕ ಅಥವಾ ಮಂಜೂರಾತಿಯ ಸಾಧ್ಯತೆಯಂತಹ ಆ ವಿಷಯದ ಬಗ್ಗೆ ಈ ಪ್ರಾತ್ಯಕ್ಷಿಕೆಯಲ್ಲಿ ನನ್ನ ಬಳಿ ಪರಿಶೀಲಿತ "
            "ಮಾಹಿತಿ ಇಲ್ಲ, ಮತ್ತು ಅವುಗಳನ್ನು ನಾನು ಊಹಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ವೆಬ್‌ಸೈಟ್‌ನಲ್ಲಿ ತೋರಿಸಿರುವ ಎಡ್ಯೂವೆಸ್ಟ್ "
            "ಸಹಾಯವಾಣಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ."
        ),
    },
}

# ---------------------------------------------------------------------
# Detecting a topic without the model (fallback)
# ---------------------------------------------------------------------
_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("eligibility_criteria", ("criteria", "who can apply", "ಯಾರು ಅರ್ಜಿ", "ಮಾನದಂಡ")),
    ("eligibility_check", ("eligible", "eligibility", "qualify", "ಅರ್ಹ")),
    ("documents", ("documents", "document", "ದಾಖಲೆ")),
    ("unknown", ("interest", "ಬಡ್ಡಿ", "approve", "approval", "ಮಂಜೂರು", "credit score", "will i get")),
]


def detect_topic(text: str) -> str | None:
    # "ಅರ್ಹತಾ ಪರೀಕ್ಷೆ" is the qualifying-exam FIELD, not an eligibility question
    lowered = text.casefold().replace("ಅರ್ಹತಾ ಪರೀಕ್ಷೆ", "")
    for topic, words in _KEYWORDS:
        if any(word in lowered for word in words):
            return topic
    return None


# ---------------------------------------------------------------------
# Criteria check: the applicant's answers vs the published criteria
# ---------------------------------------------------------------------
MET, NOT_MET, UNKNOWN = "met", "not_met", "unknown"


@dataclass
class Criterion:
    id: str
    status: str


def _num(values: dict[str, Any], key: str) -> int | float | None:
    value = values.get(key)
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _age(values: dict[str, Any]) -> int | None:
    try:
        born = date.fromisoformat(str(values.get("date_of_birth")))
    except ValueError:
        return None
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def check_criteria(values: dict[str, Any]) -> list[Criterion]:
    results: list[Criterion] = []

    age = _age(values)
    results.append(Criterion("age", UNKNOWN if age is None else (MET if 16 <= age <= 45 else NOT_MET)))

    results.append(Criterion(
        "admission", MET if values.get("admission_status") in ("confirmed", "awaiting") else UNKNOWN
    ))

    loan = _num(values, "loan_amount_requested")
    results.append(Criterion(
        "loan_amount", UNKNOWN if loan is None else (MET if 10_000 <= loan <= 15_000_000 else NOT_MET)
    ))

    tenure = _num(values, "repayment_tenure_years")
    results.append(Criterion(
        "tenure", UNKNOWN if tenure is None else (MET if 1 <= tenure <= 15 else NOT_MET)
    ))

    cost, margin = _num(values, "total_course_cost"), _num(values, "margin_money_amount")
    if loan is None or cost is None or margin is None:
        results.append(Criterion("funding_gap", UNKNOWN))
    else:
        gap = cost - margin - (_num(values, "scholarship_amount") or 0)
        results.append(Criterion("funding_gap", MET if loan <= gap else NOT_MET))

    income = _num(values, "co_applicant_annual_income")
    results.append(Criterion(
        "co_applicant", UNKNOWN if income is None else (MET if income > 0 else NOT_MET)
    ))
    return results


_LABELS = {
    "age": {"en": "Age 16 to 45", "kn": "16 ರಿಂದ 45 ವರ್ಷ ವಯಸ್ಸು"},
    "admission": {"en": "Admission confirmed or awaited", "kn": "ಪ್ರವೇಶ ಖಚಿತ ಅಥವಾ ನಿರೀಕ್ಷಿತ"},
    "loan_amount": {
        "en": "Loan amount between 10,000 and 1.5 crore rupees",
        "kn": "ಸಾಲದ ಮೊತ್ತ 10,000 ದಿಂದ 1.5 ಕೋಟಿ ರೂಪಾಯಿ",
    },
    "tenure": {"en": "Repayment period 1 to 15 years", "kn": "ಮರುಪಾವತಿ ಅವಧಿ 1 ರಿಂದ 15 ವರ್ಷ"},
    "funding_gap": {
        "en": "Loan within course cost minus margin money and scholarship",
        "kn": "ಸಾಲವು ಕೋರ್ಸ್ ವೆಚ್ಚದಿಂದ ಮಾರ್ಜಿನ್ ಮತ್ತು ವಿದ್ಯಾರ್ಥಿವೇತನ ಕಳೆದ ಮೊತ್ತದೊಳಗೆ",
    },
    "co_applicant": {"en": "Co-applicant with income", "kn": "ಆದಾಯವಿರುವ ಸಹ-ಅರ್ಜಿದಾರರು"},
}
_STATUS = {
    MET: {"en": "met", "kn": "ಪೂರೈಸಿದೆ"},
    NOT_MET: {"en": "not met", "kn": "ಪೂರೈಸಿಲ್ಲ"},
    UNKNOWN: {"en": "not given yet", "kn": "ಇನ್ನೂ ನೀಡಿಲ್ಲ"},
}
_HEADLINE = {
    "all_met": {
        "en": "Based on your answers so far, you meet all the basic criteria.",
        "kn": "ನಿಮ್ಮ ಈವರೆಗಿನ ಉತ್ತರಗಳ ಪ್ರಕಾರ, ನೀವು ಎಲ್ಲಾ ಮೂಲ ಮಾನದಂಡಗಳನ್ನು ಪೂರೈಸಿದ್ದೀರಿ.",
    },
    "some_not_met": {
        "en": "Based on your answers so far, some criteria are not met.",
        "kn": "ನಿಮ್ಮ ಈವರೆಗಿನ ಉತ್ತರಗಳ ಪ್ರಕಾರ, ಕೆಲವು ಮಾನದಂಡಗಳನ್ನು ಪೂರೈಸಿಲ್ಲ.",
    },
    "incomplete": {
        "en": "So far nothing rules you out, but I still need some answers.",
        "kn": "ಈವರೆಗೆ ನಿಮ್ಮನ್ನು ಅನರ್ಹಗೊಳಿಸುವ ಯಾವುದೂ ಇಲ್ಲ, ಆದರೆ ಇನ್ನೂ ಕೆಲವು ಉತ್ತರಗಳು ಬೇಕು.",
    },
}
_DISCLAIMER = {
    "en": (
        "This only compares your answers with the criteria on the Education Loan page. It is not an "
        "approval or an eligibility decision; the bank decides after review."
    ),
    "kn": (
        "ಇದು ಶಿಕ್ಷಣ ಸಾಲ ಪುಟದಲ್ಲಿರುವ ಮಾನದಂಡಗಳೊಂದಿಗೆ ನಿಮ್ಮ ಉತ್ತರಗಳ ಹೋಲಿಕೆ ಮಾತ್ರ. ಇದು ಮಂಜೂರಾತಿ ಅಥವಾ ಅರ್ಹತಾ "
        "ನಿರ್ಧಾರವಲ್ಲ; ಪರಿಶೀಲನೆಯ ನಂತರ ಬ್ಯಾಂಕ್ ನಿರ್ಧರಿಸುತ್ತದೆ."
    ),
}


def _eligibility_check(values: dict[str, Any], lang: str) -> str:
    results = check_criteria(values)
    statuses = {r.status for r in results}
    headline = (
        "some_not_met" if NOT_MET in statuses
        else "incomplete" if UNKNOWN in statuses
        else "all_met"
    )
    lines = " ".join(f"{_LABELS[r.id][lang]}: {_STATUS[r.status][lang]}." for r in results)
    return f"{_HEADLINE[headline][lang]} {lines} {_DISCLAIMER[lang]}"


def answer(topic: str | None, values: dict[str, Any], language: str = "en") -> str:
    """The reply text for a topic, in English or Kannada."""
    lang = "kn" if language == "kn" else "en"
    if topic == "eligibility_check":
        return _eligibility_check(values, lang)
    return TOPICS.get(topic or "", TOPICS["unknown"])[lang]