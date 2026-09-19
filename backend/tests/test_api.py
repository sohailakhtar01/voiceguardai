import io
import struct
import wave

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _tiny_wav_bytes() -> bytes:
    """1600 samples (0.1s) of silence at 16 kHz — a valid tiny WAV."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(struct.pack("<" + "h" * 1600, *([0] * 1600)))
    return buf.getvalue()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_analyze_voice_mock():
    r = client.post(
        "/api/analyze/voice",
        files={"audio": ("clip.wav", _tiny_wav_bytes(), "audio/wav")},
    )
    assert r.status_code == 200
    data = r.json()
    assert 0.0 <= data["synthetic_probability"] <= 1.0
    assert data["label"] in ("real", "synthetic")


def test_full_returns_case_metadata():
    r = client.post("/api/analyze/full", data={"transcript": "turant OTP batao aur paise bhejo"})
    assert r.status_code == 200
    d = r.json()
    assert d["case_id"].startswith("VG-")
    assert d["created_at"]
    assert d["risk"]["tier"] in ("low", "medium", "high", "critical")


def test_report_pdf_downloads():
    r = client.post("/api/report/pdf", data={"transcript": "turant OTP batao aur paise bhejo"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


def test_voices_list():
    r = client.get("/api/voices")
    assert r.status_code == 200
    assert isinstance(r.json()["voices"], list)
