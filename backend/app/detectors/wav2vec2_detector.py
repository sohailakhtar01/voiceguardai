from app.detectors.base import BaseDetector
from app.schemas import VoiceAnalysis

# NOTE: torch/transformers/soundfile are imported lazily inside __init__
# so the app runs with the mock engine even when ML libs aren't installed.
_FAKE_LABEL_KEYWORDS = ("fake", "spoof", "synthetic", "generated", "clone")


class Wav2Vec2Detector(BaseDetector):
    """Real Check-1 detector using a pretrained HuggingFace audio
    deepfake classifier. Works out of the box; later phases replace the
    model_name with our own India-fine-tuned checkpoint."""

    name = "wav2vec2"

    def __init__(self, model_name: str):
        import torch
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

        self._torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.extractor = AutoFeatureExtractor.from_pretrained(model_name)
        self.model = AutoModelForAudioClassification.from_pretrained(model_name).to(
            self.device
        )
        self.model.eval()
        self.id2label = self.model.config.id2label
        self.model_name = model_name
        self._fake_idx = self._resolve_fake_index()

    def _resolve_fake_index(self) -> int:
        """Which output index means 'fake', read from the model's own labels."""
        for idx, label in self.id2label.items():
            if any(k in str(label).lower() for k in _FAKE_LABEL_KEYWORDS):
                return int(idx)
        return 1 if len(self.id2label) > 1 else 0

    def _load_audio(self, path: str):
        # Robust loader: libsndfile fast-path + ffmpeg fallback, so ANY format
        # (M4A/AAC/Opus/MPEG/MP4 from WhatsApp/phones) decodes to 16 kHz mono.
        from app.audio_utils import load_wav16k

        return load_wav16k(path)

    def _prob_synthetic(self, wav) -> float:
        """P(fake) for one waveform chunk (already 16 kHz mono)."""
        torch = self._torch
        inputs = self.extractor(wav, sampling_rate=16000, return_tensors="pt").to(
            self.device
        )
        with torch.no_grad():
            logits = self.model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        return float(probs[self._fake_idx])

    def analyze(self, audio_path: str) -> VoiceAnalysis:
        wav = self._load_audio(audio_path)
        synthetic_prob = self._prob_synthetic(wav)
        is_syn = synthetic_prob >= 0.5
        return VoiceAnalysis(
            is_synthetic=is_syn,
            synthetic_probability=round(synthetic_prob, 4),
            label="synthetic" if is_syn else "real",
            confidence=round(abs(synthetic_prob - 0.5) * 2, 4),
            model=self.model_name,
            detail={"device": self.device, "labels": self.id2label},
        )

    @staticmethod
    def _rms(x) -> float:
        import numpy as np

        return float(np.sqrt(np.mean(x**2))) if len(x) else 0.0

    def analyze_windows(
        self, audio_path: str, window_s: float = 1.5, threshold: float = 0.5
    ) -> list[dict]:
        """Segment-level (timeline) analysis: split into short non-overlapping
        windows and classify each, so a clip that mixes real + AI speech shows
        *which* seconds are synthetic instead of one whole-clip verdict.

        Accuracy hardening:
          * low-energy (silent) windows are gated out — they get unreliable
            predictions once wav2vec2 normalises near-silence, so we mark them
            'speech: false' and exclude them from the verdict;
          * a majority-smoothing pass fixes a lone window that disagrees with
            both of its speech neighbours (removes jumpy single-window flips).
        """
        sr = 16000
        wav = self._load_audio(audio_path)
        n = len(wav)
        w = int(window_s * sr)
        min_tail = int(0.5 * sr)  # don't leave a scrap window < 0.5 s

        if n <= w:
            spans = [(0, n)]
        else:
            spans = [(i, min(i + w, n)) for i in range(0, n, w)]
            if spans[-1][1] - spans[-1][0] < min_tail and len(spans) > 1:
                last = spans.pop()
                spans[-1] = (spans[-1][0], last[1])

        # Speech vs silence gate — adaptive floor relative to the loudest window.
        energies = [self._rms(wav[a:b]) for a, b in spans]
        peak = max(energies) if energies else 0.0
        floor = max(0.004, 0.15 * peak)

        segments = []
        for (a, b), e in zip(spans, energies):
            seg = {"start": round(a / sr, 2), "end": round(b / sr, 2)}
            if e < floor:
                seg.update(synthetic_probability=None, is_synthetic=False, speech=False)
            else:
                p = self._prob_synthetic(wav[a:b])
                seg.update(
                    synthetic_probability=round(p, 4),
                    is_synthetic=p >= threshold,
                    speech=True,
                )
            segments.append(seg)

        # Majority smoothing: only correct a window sandwiched between TWO
        # opposite speech windows (a genuine isolated flip). A single neighbour
        # is never enough — that would erase a real AI/human boundary.
        labels = [s["is_synthetic"] for s in segments]
        for i, s in enumerate(segments):
            if not s["speech"]:
                continue
            neighbours = [
                labels[j]
                for j in (i - 1, i + 1)
                if 0 <= j < len(segments) and segments[j]["speech"]
            ]
            if len(neighbours) == 2 and all(nb != labels[i] for nb in neighbours):
                s["is_synthetic"] = neighbours[0]
        return segments
