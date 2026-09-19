from typing import Literal, Optional
from pydantic import BaseModel, Field


class VoiceAnalysis(BaseModel):
    """Check 1 — is this voice AI-synthetic?"""

    is_synthetic: bool
    synthetic_probability: float = Field(..., ge=0.0, le=1.0)
    label: Literal["real", "synthetic"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    model: str
    detail: Optional[dict] = None


class IdentityResult(BaseModel):
    """Check 2 — does the voice match the claimed person?"""

    checked: bool
    similarity: Optional[float] = None
    identity_match: Optional[bool] = None
    mismatch_risk: float = Field(0.0, ge=0.0, le=1.0)
    source: Optional[str] = None
    note: Optional[str] = None


class IntentResult(BaseModel):
    """Check 3 — is the caller asking for something dangerous?"""

    transcript: str
    language_hint: Optional[str] = None
    triggered: list[str]
    intent_risk: float = Field(..., ge=0.0, le=1.0)
    matches: dict
    note: Optional[str] = None


class RiskResult(BaseModel):
    """Layer 4 — the combined, explained verdict."""

    overall_risk: float = Field(..., ge=0.0, le=1.0)
    tier: Literal["low", "medium", "high", "critical"]
    response: str
    breakdown: dict
    reasons: list[str]


class FullAnalysis(BaseModel):
    voice: VoiceAnalysis
    identity: Optional[IdentityResult] = None
    intent: Optional[IntentResult] = None
    risk: RiskResult
