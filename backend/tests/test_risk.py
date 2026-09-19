from app.intent.analyzer import detect_intent
from app.risk.engine import compute_risk
from app.schemas import IdentityResult, VoiceAnalysis


def _voice(prob: float) -> VoiceAnalysis:
    is_syn = prob >= 0.5
    return VoiceAnalysis(
        is_synthetic=is_syn,
        synthetic_probability=prob,
        label="synthetic" if is_syn else "real",
        confidence=abs(prob - 0.5) * 2,
        model="test",
    )


def test_clean_call_is_low_risk():
    voice = _voice(0.1)
    intent = detect_intent("Hey, calling to say happy birthday!")
    risk = compute_risk(voice, None, intent)
    assert risk.tier == "low"


def test_fake_voice_plus_scam_is_high_or_critical():
    voice = _voice(0.95)
    intent = detect_intent("Turant OTP batao aur paise bhejo, urgent!")
    risk = compute_risk(voice, None, intent)
    assert risk.tier in ("high", "critical")
    assert risk.overall_risk > 0.6


def test_identity_mismatch_adds_risk():
    voice = _voice(0.6)
    intent = detect_intent("please send money")
    mismatch = IdentityResult(
        checked=True, similarity=0.05, identity_match=False, mismatch_risk=0.95
    )
    with_id = compute_risk(voice, mismatch, intent)
    without_id = compute_risk(voice, None, intent)
    assert with_id.overall_risk > without_id.overall_risk


def test_missing_identity_is_not_penalised():
    # When identity isn't checked, its weight is redistributed, not assumed.
    voice = _voice(0.1)
    intent = detect_intent("normal friendly chat")
    risk = compute_risk(voice, None, intent)
    assert risk.overall_risk < 0.3
    assert "identity" not in risk.breakdown


def test_scam_ask_escalates_even_when_voice_sounds_human():
    # A good clone can fool the voice check (0% AI) and match the voiceprint,
    # but asking for OTP + money together must still be flagged high/critical —
    # the request is the red flag, regardless of how human the voice sounds.
    voice = _voice(0.0)  # voice check fooled by the clone
    match = IdentityResult(checked=True, similarity=0.6, identity_match=True, mismatch_risk=0.4)
    intent = detect_intent("beta turant OTP batao aur paise transfer karo")
    risk = compute_risk(voice, match, intent)
    assert risk.tier in ("high", "critical")
    assert any("Escalated" in r for r in risk.reasons)
