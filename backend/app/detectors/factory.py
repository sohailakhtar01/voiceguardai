from functools import lru_cache
from app.config import settings
from app.detectors.base import BaseDetector
from app.detectors.mock_detector import MockDetector


@lru_cache
def get_detector() -> BaseDetector:
    """Return the active Check-1 detector, chosen by DETECTOR_ENGINE.
    Cached so the (possibly heavy) model loads only once per process."""
    engine = settings.detector_engine.strip().lower()
    if engine == "mock":
        return MockDetector()
    if engine == "wav2vec2":
        from app.detectors.wav2vec2_detector import Wav2Vec2Detector

        return Wav2Vec2Detector(settings.wav2vec2_model)
    raise ValueError(
        f"Unknown DETECTOR_ENGINE '{engine}'. Use 'mock' or 'wav2vec2'."
    )
