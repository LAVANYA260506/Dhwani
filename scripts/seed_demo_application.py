"""
Creates a complete demo application through the real API.

    python scripts\seed_demo_application.py            fill everything
    python scripts\seed_demo_application.py --skip pan_number,email   leave some fields empty

Prints a one-line browser snippet that logs the browser into this application,
so you can open /application/review straight away.
"""

import sys

import requests

BASE = "http://localhost:8000/api"
SKIP = set()
if "--skip" in sys.argv:
    SKIP = set(sys.argv[sys.argv.index("--skip") + 1].split(","))

# Fields that other fields depend on come first
VALUES = [
    ("study_country", "india"), ("permanent_address_same", "yes"), ("admission_type", "merit"),
    ("has_backlogs", "no"), ("collateral_offered", "no"),
    ("full_name", "Lavanya Hegde"), ("father_name", "Ananda Hegde"), ("mother_name", "Manjula Hegde"),
    ("date_of_birth", "14-05-2003"), ("gender", "female"), ("marital_status", "single"),
    ("nationality", "indian"), ("category", "obc"), ("aadhaar_number", "234567890123"),
    ("mobile_number", "9876543210"), ("email", "lavanya@example.com"),
    ("current_address_line1", "12 MG Road"), ("current_city", "Mysuru"),
    ("current_state", "Karnataka"), ("current_pincode", "570001"),
    ("institution_name", "Visvesvaraya Technological University"), ("institution_type", "government"),
    ("course_name", "M.Tech in Computer Science"), ("course_level", "pg"),
    ("course_duration_years", 2), ("course_start_year", 2026),
    ("admission_status", "confirmed"),
    ("qualifying_exam", "bachelors"), ("board_or_university", "Visvesvaraya Technological University"),
    ("register_number", "1MY21CS045"), ("year_of_passing", 2025),
    ("marks_obtained", 512), ("max_marks", 600),
    ("tenth_percentage", 88), ("twelfth_percentage", 85),
    ("tuition_fee_total", 400000), ("hostel_fee_total", 120000), ("books_equipment_cost", 30000),
    ("loan_amount_requested", 300000), ("repayment_tenure_years", 7),
    ("moratorium_acknowledged", True), ("margin_money_amount", 50000), ("margin_source", "family"),
    ("other_loans_for_education", "no"),
    ("co_applicant_name", "Ananda Hegde"), ("co_applicant_relationship", "father"),
    ("co_applicant_dob", "10-03-1975"), ("co_applicant_pan", "ABCPE1234F"),
    ("co_applicant_mobile", "9876501234"), ("co_applicant_occupation", "Farmer"),
    ("co_applicant_employer_or_business", "Self employed"),
    ("co_applicant_annual_income", 400000), ("co_applicant_existing_emi", 1500),
    ("declaration_info_true", True), ("declaration_consent_credit_check", True),
    ("declaration_terms_accepted", True),
]

created = requests.post(f"{BASE}/applications", json={"language": "en", "consent_given": True}).json()
token = created["session_token"]
headers = {"Authorization": f"Bearer {token}"}

problems = 0
for field_id, value in VALUES:
    if field_id in SKIP:
        continue
    result = requests.put(
        f"{BASE}/applications/me/fields", headers=headers,
        json={"field_id": field_id, "value": value, "source": "text"},
    ).json()
    if not result.get("accepted"):
        problems += 1
        print(f"  NOT ACCEPTED {field_id}={value!r}: {[i['message'] for i in result.get('issues', [])]}")

state = requests.get(f"{BASE}/applications/me", headers=headers).json()
progress = state["progress"]
print(f"\nProgress: {progress['answered_required']}/{progress['total_required']}, complete: {progress['complete']}, status: {state['status']}")

review = requests.get(f"{BASE}/submission/review", headers=headers).json()
print(f"Ready to submit: {review['ready']}")
for issue in review["issues"]:
    print("  -", issue["kind"], issue["label"], ":", issue["message"])

print("\nPaste this in the browser console (F12) on http://localhost:3000, then open /application/review:")
print(f"localStorage.setItem('dhwani_session_token', '{token}')")