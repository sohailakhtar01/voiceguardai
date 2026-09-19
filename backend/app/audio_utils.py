"""Robust audio loading — accepts any format the demo may throw at it.

WhatsApp and phones re-encode clips to M4A/AAC, OGG/Opus, MPEG, MP4, AMR…
libsndfile (via librosa/soundfile) only handles WAV/FLAC/OGG/MP3, so we fall
back to a bundled ffmpeg binary that decodes essentially everything.
"""
import os
import subprocess
import tempfile

TARGET_SR = 16000

_ffmpeg_exe = None


def ffmpeg_path() -> str:
    """Locate an ffmpeg binary: system PATH first, else the pip-bundled one."""
    global _ffmpeg_exe
    if _ffmpeg_exe is not None:
        return _ffmpeg_exe
    from shutil import which

    exe = which("ffmpeg")
    if exe is None:
        try:
            import imageio_ffmpeg

            exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            exe = ""
    _ffmpeg_exe = exe or ""
    return _ffmpeg_exe


def _load_via_ffmpeg(path: str):
    import numpy as np
    import soundfile as sf

    exe = ffmpeg_path()
    if not exe:
        raise RuntimeError("Unsupported audio format and no ffmpeg available.")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.close()
    try:
        subprocess.run(
            [exe, "-y", "-hide_banner", "-loglevel", "error",
             "-i", path, "-ac", "1", "-ar", str(TARGET_SR), tmp.name],
            capture_output=True, check=True,
        )
        wav, _ = sf.read(tmp.name, dtype="float32", always_2d=True)
        return wav.mean(axis=1).astype("float32")
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def load_wav16k(path: str):
    """Return float32 mono waveform at 16 kHz for ANY input format.

    Fast path: librosa/libsndfile (WAV/FLAC/OGG/MP3).
    Fallback: ffmpeg (M4A/AAC/Opus/MPEG/MP4/AMR/WEBM/…).
    """
    try:
        import librosa

        wav, _ = librosa.load(path, sr=TARGET_SR, mono=True)
        if wav is not None and len(wav) > 0:
            return wav
    except Exception:
        pass
    return _load_via_ffmpeg(path)
