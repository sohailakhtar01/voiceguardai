"""Check 2 — speaker identity verification via SpeechBrain ECAPA-TDNN.

ML libs are imported lazily so the app runs without them. Pass RELATIVE
audio paths on Windows (SpeechBrain misreads 'C:\\...' as a URL)."""

from app.schemas import IdentityResult

MODEL_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"
MODEL_SAVEDIR = "models/spkrec-ecapa-voxceleb"
# Calibrated on real samples: different speaker ~0.28, same speaker ~0.54,
# so the cutoff sits between them. Cleaner/longer enrollment clips raise the
# same-speaker score and widen this margin.
MATCH_THRESHOLD = 0.40


class SpeakerVerifier:
    def __init__(self):
        from speechbrain.inference.speaker import SpeakerRecognition
        from speechbrain.utils.fetching import LocalStrategy

        self.model = SpeakerRecognition.from_hparams(
            source=MODEL_SOURCE,
            savedir=MODEL_SAVEDIR,
            local_strategy=LocalStrategy.COPY,  # Windows: no symlink perms needed
        )

    def extract_embedding(self, audio_path: str):
        # Load via our own loader (16 kHz mono, any format incl. WhatsApp) instead
        # of model.load_audio — that avoids SpeechBrain's Windows 'C:\...'-as-URL bug
        # and its torchaudio backend requirement.
        import torch

        from app.audio_utils import load_wav16k

        wav = load_wav16k(audio_path)
        signal = torch.tensor(wav, dtype=torch.float32).unsqueeze(0)  # [1, T]
        return self.model.encode_batch(signal).squeeze().detach().cpu()

    def embedding_list(self, audio_path: str) -> list:
        """Voiceprint as a plain list of floats — for the registry (JSON/Supabase)."""
        return self.extract_embedding(audio_path).flatten().tolist()

    def _result(self, sim: float, source: str) -> IdentityResult:
        return IdentityResult(
            checked=True,
            similarity=round(sim, 4),
            identity_match=sim >= MATCH_THRESHOLD,
            mismatch_risk=round(1.0 - max(0.0, min(1.0, sim)), 4),
            source=source,
        )

    def compare_paths(self, audio_path: str, reference_path: str) -> IdentityResult:
        import torch

        a = self.extract_embedding(audio_path)
        b = self.extract_embedding(reference_path)
        sim = float(torch.nn.functional.cosine_similarity(a.flatten(), b.flatten(), dim=0))
        return self._result(sim, "reference")

    def compare_to_embedding(self, audio_path: str, stored_embedding: list) -> IdentityResult:
        import torch

        a = self.extract_embedding(audio_path)
        b = torch.tensor(stored_embedding, dtype=a.dtype)
        sim = float(torch.nn.functional.cosine_similarity(a.flatten(), b.flatten(), dim=0))
        return self._result(sim, "registry")
