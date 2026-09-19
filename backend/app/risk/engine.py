from typing import Optional

from app.schemas import IdentityResult, IntentResult, RiskResult, VoiceAnalysis

# Starting weights (NOT yet validated against labelled data — we tune these
# in Phase 5 and report honest numbers, never a fake accuracy figure).
WEIGHTS = {"voice": 0.35, "identity": 0.25, "intent": 0.40}


def compute_risk(
    voice: Optional[VoiceAnalysis],
    identity: Optional[IdentityResult],
    intent: Optional[IntentResult],
) -> RiskResult:
    """Combine whichever checks were actually measured into one explained
    risk score. Missing signals have their weight redistributed rather than
    assumed, so the score stays fair when (say) no audio or no reference
    voiceprint was provided."""
    signals: dict[str, tuple[float, float]] = {}
    if voice is not None:
        signals["voice"] = (WEIGHTS["voice"], voice.synthetic_probability)
    if identity is not None and identity.checked:
        signals["identity"] = (WEIGHTS["identity"], identity.mismatch_risk)
    if intent is not None:
        signals["intent"] = (WEIGHTS["intent"], intent.intent_risk)

    if not signals:
        return RiskResult(
            overall_risk=0.0,
            tier="low",
            response="No signals provided.",
            breakdown={},
            reasons=["Nothing to analyze — provide audio and/or a transcript."],
        )

    total_w = sum(w for w, _ in signals.values())
    overall = round(min(1.0, sum(w * r for w, r in signals.values()) / total_w), 4)

    reasons: list[str] = []
    if voice is not None and voice.synthetic_probability >= 0.5:
        reasons.append(
            f"Voice sounds AI-synthetic (~{voice.synthetic_probability:.0%} fake)."
        )
    if identity is not None and identity.checked and identity.identity_match is False:
        reasons.append("Voice does NOT match the claimed person's voiceprint.")
    if intent is not None and intent.triggered:
        reasons.append(
            "Suspicious request detected: " + ", ".join(intent.triggered) + "."
        )
    if not reasons:
        reasons.append("No strong impersonation signals found.")

    if overall < 0.30:
        tier, response = "low", "No interruption — looks normal."
    elif overall < 0.55:
        tier, response = "medium", "Show a caution warning to the user."
    elif overall < 0.80:
        tier, response = "high", "Ask the user to independently verify the caller."
    else:
        tier, response = (
            "critical",
            "Block and force step-up verification before any action.",
        )

    # --- Prevention override: the ASK itself is the red flag ---
    # A genuine caller does not need BOTH your OTP and your money. This classic
    # fraud combo is escalated no matter how human the voice sounds — because a
    # good clone fools acoustic checks, but the request does not. If the ask is
    # also urgent / from a claimed authority / demands secrecy, treat as critical.
    if intent is not None and "otp_request" in intent.triggered and "money_request" in intent.triggered:
        severe = bool({"urgency", "authority_claim", "secrecy"} & set(intent.triggered))
        forced = "critical" if severe else "high"
        _rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        if _rank[forced] > _rank[tier]:
            tier = forced
            overall = max(overall, 0.85 if forced == "critical" else 0.70)
            response = (
                "Block and force step-up verification before any action."
                if forced == "critical"
                else "Ask the user to independently verify the caller."
            )
            reasons.append(
                "Escalated: caller asked for OTP + money together — the classic fraud "
                "pattern — flagged regardless of how human the voice sounds."
            )

    return RiskResult(
        overall_risk=overall,
        tier=tier,
        response=response,
        breakdown={
            **{k: round(r, 4) for k, (_, r) in signals.items()},
            "weights_used": {k: w for k, (w, _) in signals.items()},
        },
        reasons=reasons,
    )
