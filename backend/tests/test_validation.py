"""Unit tests for the validation engine. Run from backend/:  python -m pytest tests -q"""

from app.services import validation_service as v


def ok(field_id, value, values=None, language="en"):
    clean, issues = v.validate_field(field_id, value, values or {}, language)
    assert not issues, f"{field_id}={value!r} -> {[i.code for i in issues]}"
    return clean


def bad(field_id, value, values=None, language="en"):
    clean, issues = v.validate_field(field_id, value, values or {}, language)
    assert issues, f"{field_id}={value!r} should be rejected"
    assert clean is None
    return issues[0]


def test_phone_formats():
    assert ok("mobile_number", "9876543210") == "9876543210"
    assert ok("mobile_number", "+91 98765 43210") == "9876543210"
    assert ok("mobile_number", "098765-43210") == "9876543210"
    assert bad("mobile_number", "12345").code == "invalid_phone"
    assert bad("mobile_number", "5876543210").code == "invalid_phone"


def test_email_typed_and_spoken():
    assert ok("email", "Test@Example.com") == "test@example.com"
    assert ok("email", "lavanya at gmail dot com") == "lavanya@gmail.com"
    assert bad("email", "not-an-email").code == "invalid_email"


def test_pincode_pan_aadhaar():
    assert ok("current_pincode", "560 001") == "560001"
    assert bad("current_pincode", "056001").code == "invalid_pincode"
    assert ok("pan_number", "abcpe1234f") == "ABCPE1234F"
    assert bad("pan_number", "ABCDE1234F").code == "invalid_pan"
    assert ok("aadhaar_number", "2345 6789 0123") == "234567890123"
    assert bad("aadhaar_number", "1234 5678 9012").code == "invalid_aadhaar"


def test_dates_and_age():
    assert ok("date_of_birth", "14-05-2003") == "2003-05-14"
    assert ok("date_of_birth", "14 May 2003") == "2003-05-14"
    assert ok("date_of_birth", "14th May, 2003") == "2003-05-14"
    assert bad("date_of_birth", "01-01-2099").code == "date_in_future"
    assert bad("date_of_birth", "01-01-2020").code == "age_out_of_range"
    assert bad("date_of_birth", "tomorrow-ish").code == "invalid_date"


def test_numbers_and_ranges():
    assert ok("loan_amount_requested", "5 lakh") == 500000
    assert ok("loan_amount_requested", "\u20b97,00,000") == 700000
    assert bad("loan_amount_requested", "5000").code == "below_minimum"
    assert bad("marks_obtained", "abc").code == "invalid_number"
    assert ok("entrance_exam_rank", "1,234") == 1234
    assert bad("entrance_exam_rank", "12.5").code == "not_integer"
    assert ok("year_of_passing", "2023") == 2023
    assert bad("year_of_passing", "2999").code == "above_maximum"


def test_choices_by_value_and_kannada_label():
    assert ok("gender", "Female") == "female"
    assert ok("gender", "\u0caa\u0cc1\u0cb0\u0cc1\u0cb7") == "male"  # ಪುರುಷ
    assert ok("disability_status", "yeah") == "yes"
    assert bad("gender", "robot").code == "invalid_choice"


def test_required_checkbox_must_be_ticked():
    assert ok("declaration_info_true", "yes") is True
    assert bad("declaration_info_true", "no").code == "must_accept"


def test_wrong_field_detection():
    issue = bad("full_name", "9876543210")
    assert issue.code == "wrong_field"
    assert issue.suggested_field == "mobile_number"

    issue = bad("mobile_number", "ABCPE1234F")
    assert issue.code == "wrong_field"
    assert issue.suggested_field == "pan_number"

    issue = bad("full_name", "Lavanya 123")
    assert issue.code == "invalid_name"


def test_register_number_is_not_flagged_as_phone():
    assert ok("register_number", "9876543210") == "9876543210"
    assert ok("register_number", "1sj21cs045") == "1SJ21CS045"


def test_kannada_messages():
    issue = bad("mobile_number", "123", language="kn")
    assert any("\u0c80" <= ch <= "\u0cff" for ch in issue.message)
    assert issue.hint


def test_cross_field_rules():
    values = {"marks_obtained": 500, "max_marks": 450}
    issues = v.check_cross_rules(values, "en", changed_field="max_marks")
    assert issues and issues[0].code == "cross_field"
    assert not v.check_cross_rules({"marks_obtained": 500, "max_marks": 600}, "en")
    # Not enough answers yet: nothing to complain about
    assert not v.check_cross_rules({"marks_obtained": 500}, "en")


def test_loan_cannot_exceed_funding_gap():
    values = {
        "loan_amount_requested": 900000,
        "total_course_cost": 1000000,
        "margin_money_amount": 200000,
    }
    assert v.find_cross_violations(values)[0].rule_id == "loan_within_funding_gap"
    values["loan_amount_requested"] = 800000
    assert not v.find_cross_violations(values)