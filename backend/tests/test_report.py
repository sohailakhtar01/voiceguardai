from app.report.generator import build_report, new_case_id, render_pdf, utc_now


def _sample_report():
    risk = {
        "tier": "high",
        "overall_risk": 0.72,
        "response": "Ask the user to independently verify the caller.",
        "reasons": ["Suspicious request detected: otp_request, money_request."],
        "breakdown": {"voice": 0.9, "intent": 1.0},
    }
    return build_report(
        new_case_id(),
        utc_now(),
        "a" * 64,
        {"label": "synthetic", "synthetic_probability": 0.9},
        None,
        {"transcript": "turant OTP batao", "triggered": ["otp_request"],
         "intent_risk": 1.0, "matches": {"otp_request": "OTP"}},
        risk,
    )


def test_build_report_structure():
    rep = _sample_report()
    assert rep["case_id"].startswith("VG-")
    assert rep["verdict"]["tier"] == "high"
    assert rep["disclaimer"]


def test_render_pdf_is_a_pdf():
    pdf = render_pdf(_sample_report())
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000
