"""Verify the REAL wav2vec2 detector works — run AFTER installing the ML deps.

    pip install -r requirements-ml.txt
    python scripts/verify_model.py

Generates a short tone, loads the pretrained model, and prints a real result.
Confirms Phase 1b is live before you flip DETECTOR_ENGINE=wav2vec2 in the API.
"""

import math
import os
import struct
import tempfile
import wave


def make_tone(path, freq=220, secs=2, sr=16000):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        frames = [int(30000 * math.sin(2 * math.pi * freq * t / sr)) for t in range(sr * secs)]
        w.writeframes(struct.pack("<%dh" % len(frames), *frames))


if __name__ == "__main__":
    from app.config import settings
    from app.detectors.wav2vec2_detector import Wav2Vec2Detector

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.close()
    make_tone(tmp.name)
    try:
        print("Loading model:", settings.wav2vec2_model)
        d = Wav2Vec2Detector(settings.wav2vec2_model)
        print("Loaded on device:", d.device)
        print("Result:", d.analyze(tmp.name).model_dump())
        print("OK — real detector works. Set DETECTOR_ENGINE=wav2vec2 in .env")
    finally:
        os.unlink(tmp.name)
