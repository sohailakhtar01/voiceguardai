from abc import ABC, abstractmethod
from app.schemas import VoiceAnalysis


class BaseDetector(ABC):
    """Interface every Check-1 detector implements, so the API code
    never depends on which engine (mock / wav2vec2 / future) is active."""

    name: str = "base"

    @abstractmethod
    def analyze(self, audio_path: str) -> VoiceAnalysis:
        """Return a synthetic-voice analysis for the audio file at audio_path."""
        raise NotImplementedError
