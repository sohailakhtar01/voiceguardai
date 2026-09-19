from app.intent.analyzer import detect_intent


def test_benign_text_low_risk():
    r = detect_intent("Hi, are we still meeting for lunch tomorrow?")
    assert r.triggered == []
    assert r.intent_risk == 0.0


def test_english_scam_flagged():
    r = detect_intent("This is urgent, share your OTP and transfer money now.")
    assert "otp_request" in r.triggered
    assert "money_request" in r.triggered
    assert "urgency" in r.triggered
    assert r.intent_risk > 0.5


def test_hindi_codemixed_scam_flagged():
    # The India differentiator: romanized/code-mixed scam speech.
    r = detect_intent("Sir turant OTP batao aur paise transfer karo, urgent hai.")
    assert "otp_request" in r.triggered
    assert "money_request" in r.triggered
    assert "urgency" in r.triggered
    assert r.intent_risk > 0.5


def test_devanagari_terms_flagged():
    r = detect_intent("कृपया तुरंत ओटीपी बताओ")
    assert "otp_request" in r.triggered
    assert "urgency" in r.triggered


def test_tamil_romanized_scam_flagged():
    r = detect_intent("udane OTP sollu, panam transfer pannu")
    assert "otp_request" in r.triggered
    assert "money_request" in r.triggered
    assert "urgency" in r.triggered


def test_telugu_romanized_scam_flagged():
    r = detect_intent("ventane OTP cheppu, dabbulu pampu")
    assert "otp_request" in r.triggered
    assert "money_request" in r.triggered
    assert "urgency" in r.triggered


def test_urdu_scam_flagged():
    r = detect_intent("fauran OTP bhejo aur rupiya transfer karo")
    assert "otp_request" in r.triggered
    assert "money_request" in r.triggered
    assert "urgency" in r.triggered
