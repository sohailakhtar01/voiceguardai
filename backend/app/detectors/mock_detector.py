import hashlib
from app.detectors.base import BaseDetector
from app.schemas import VoiceAnalysis


class MockDetector(BaseDetector):
    """Deterministic placeholder — no ML, no GPU, no downloads.

    Produces a stable pseudo-score from the file's bytes so the whole
    app (API + frontend) can be built and demoed before the real model
    is installed. Swap DETECTOR_ENGINE=wav2vec2 for actual detection.
    """

    name = "mock"

    def analyze(self, audio_path: str) -> VoiceAnalysis:
        with open(audio_path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        prob = int(digest[:4], 16) / 0xFFFF  # stable 0..1 from file content
        is_syn = prob >= 0.5
        return VoiceAnalysis(
            is_synthetic=is_syn,
            synthetic_probability=round(prob, 4),
            label="synthetic" if is_syn else "real",
            confidence=round(abs(prob - 0.5) * 2, 4),
            model="mock-v1 (deterministic placeholder, not real ML)",
            detail={"note": "Set DETECTOR_ENGINE=wav2vec2 for real detection."},
        )
