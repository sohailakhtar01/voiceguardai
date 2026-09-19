import re

from app.intent.patterns import INTENT_PATTERNS
from app.schemas import IntentResult

_COMPILED = {
    cat: [re.compile(p, re.IGNORECASE) for p in pats]
    for cat, pats in INTENT_PATTERNS.items()
}


def detect_intent(transcript: str) -> IntentResult:
    """Rule-based scam-intent detection on a transcript. Pure Python —
    works with zero ML installed, so we can demo Hindi/code-mixed
    detection immediately."""
    text = transcript or ""
    triggered: list[str] = []
    matches: dict[str, str] = {}
    for cat, regexes in _COMPILED.items():
        for rx in regexes:
            m = rx.search(text)
            if m:
                triggered.append(cat)
                matches[cat] = m.group(0)
                break

    # Each distinct scam signal adds risk; OTP + money together is the
    # classic fraud combo, so bump it.
    risk = 0.28 * len(triggered)
    if "otp_request" in triggered and "money_request" in triggered:
        risk += 0.2
    risk = round(min(1.0, risk), 4)

    return IntentResult(
        transcript=text,
        triggered=triggered,
        intent_risk=risk,
        matches=matches,
    )


class IntentAnalyzer:
    """Transcribe (faster-whisper, loaded lazily) then detect intent.
    The text path needs no ML at all."""

    def __init__(self, whisper_size: str = "small"):
        self._whisper_size = whisper_size
        self._model = None

    def _model_or_load(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            # device="cpu" is required — without it ctranslate2 tries to load CUDA
            # (cublas64_*.dll) and crashes on CPU-only machines.
            self._model = WhisperModel(self._whisper_size, device="cpu", compute_type="int8")
        return self._model

    def analyze_text(self, transcript: str) -> IntentResult:
        return detect_intent(transcript)

    def analyze_audio(self, audio_path: str) -> IntentResult:
        model = self._model_or_load()
        segments, info = model.transcribe(audio_path, beam_size=5)
        transcript = " ".join(seg.text.strip() for seg in segments)
        result = detect_intent(transcript)
        result.language_hint = getattr(info, "language", None)
        return result
