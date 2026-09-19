import hashlib
import os
import shutil
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.config import settings
from app.detectors.factory import get_detector
from app.identity import registry
from app.intent.analyzer import IntentAnalyzer
from app.report.generator import build_report, new_case_id, render_pdf, sha256_bytes, utc_now
from app.risk.engine import compute_risk
from app.schemas import IdentityResult, IntentResult
from app.storage import save_analysis

app = FastAPI(title="VoiceGuard AI — Detection API", version="0.3.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

_intent_analyzer = IntentAnalyzer()
_verifier = None
_verifier_error = None


def _get_verifier():
    """Build the speaker verifier once; None if ML libs (speechbrain) missing."""
    global _verifier, _verifier_error
    if _verifier is None and _verifier_error is None:
        try:
            from app.identity.verifier import SpeakerVerifier

            _verifier = SpeakerVerifier()
        except Exception as exc:
            _verifier_error = str(exc)
    return _verifier


def _save_upload(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "clip.wav")[1] or ".wav"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    shutil.copyfileobj(upload.file, tmp)
    tmp.close()
    return tmp.name


def _sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


def _resolve_identity(path, ref, claimed):
    """Check 2. claimed → registry voiceprint; else ref clip; else skip."""
    if claimed:
        stored = registry.load_voiceprint(claimed)
        if stored is None:
            return IdentityResult(checked=False, note=f"'{claimed}' is not registered.")
        v = _get_verifier()
        if v is None:
            return IdentityResult(checked=False, note=f"Needs speechbrain: {_verifier_error}")
        return v.compare_to_embedding(path, stored)
    if ref:
        v = _get_verifier()
        if v is None:
            return IdentityResult(checked=False, note=f"Needs speechbrain: {_verifier_error}")
        return v.compare_paths(path, ref)
    return None


def _run_pipeline(path, transcript, ref, claimed):
    voice = get_detector().analyze(path) if path else None
    if transcript:
        intent = _intent_analyzer.analyze_text(transcript)
    elif path:
        try:
            intent = _intent_analyzer.analyze_audio(path)
        except Exception as exc:
            intent = IntentResult(
                transcript="", triggered=[], intent_risk=0.0, matches={},
                note=f"Transcription unavailable (install faster-whisper): {exc}",
            )
    else:
        intent = None
    identity = _resolve_identity(path, ref, claimed) if path else None
    risk = compute_risk(voice, identity, intent)
    return voice, identity, intent, risk


def _voice_timeline(path):
    """Per-second AI/human timeline + AI fraction for a voice clip."""
    if not path:
        return None
    detector = get_detector()
    if not hasattr(detector, "analyze_windows"):
        return None
    segments = detector.analyze_windows(path)
    if not segments:
        return None
    speech = [s for s in segments if s.get("speech", True)]
    ai = sum(1 for s in speech if s["is_synthetic"])
    return {
        "segments": segments,
        "speech_windows": len(speech),
        "synthetic_fraction": round(ai / len(speech), 4) if speech else 0.0,
    }


@app.get("/health")
def health():
    return {"status": "ok", "engine": settings.detector_engine}


@app.post("/api/analyze/voice")
async def analyze_voice(audio: UploadFile = File(...)):
    path = _save_upload(audio)
    try:
        result = get_detector().analyze(path).model_dump()
        tl = _voice_timeline(path)
        if tl:
            result.update(tl)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        os.unlink(path)


@app.post("/api/analyze/intent")
async def analyze_intent(audio: UploadFile = File(None), transcript: str = Form(None)):
    if transcript:
        return _intent_analyzer.analyze_text(transcript)
    if audio is None:
        raise HTTPException(status_code=400, detail="Provide 'transcript' or 'audio'.")
    path = _save_upload(audio)
    try:
        return _intent_analyzer.analyze_audio(path)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Needs faster-whisper: {exc}")
    finally:
        os.unlink(path)


@app.post("/api/analyze/full")
async def analyze_full(
    audio: UploadFile = File(None),
    transcript: str = Form(None),
    reference_audio: UploadFile = File(None),
    claimed_identity: str = Form(None),
):
    """Main pipeline → explained risk score + forensic case metadata."""
    if audio is None and not transcript:
        raise HTTPException(status_code=400, detail="Provide 'audio' and/or 'transcript'.")
    path = _save_upload(audio) if audio is not None else None
    ref = _save_upload(reference_audio) if reference_audio else None
    try:
        voice, identity, intent, risk = _run_pipeline(path, transcript, ref, claimed_identity)
        case_id, created_at = new_case_id(), utc_now()
        audio_sha256 = _sha256_file(path) if path else None
        save_analysis({  # best-effort; no-op unless Supabase is configured
            "case_id": case_id,
            "created_at": created_at,
            "audio_sha256": audio_sha256,
            "tier": risk.tier,
            "overall_risk": risk.overall_risk,
            "triggered": intent.triggered if intent else [],
            "transcript": intent.transcript if intent else None,
        })
        voice_out = voice.model_dump() if voice else None
        tl = _voice_timeline(path)
        if voice_out and tl:
            voice_out.update(tl)
        return {
            "case_id": case_id,
            "created_at": created_at,
            "audio_sha256": audio_sha256,
            "voice": voice_out,
            "identity": identity,
            "intent": intent,
            "risk": risk,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if path:
            os.unlink(path)
        if ref:
            os.unlink(ref)


@app.post("/api/report/pdf")
async def report_pdf(
    audio: UploadFile = File(None),
    transcript: str = Form(None),
    reference_audio: UploadFile = File(None),
    claimed_identity: str = Form(None),
):
    """Same inputs as /analyze/full → a downloadable PDF forensic report."""
    if audio is None and not transcript:
        raise HTTPException(status_code=400, detail="Provide 'audio' and/or 'transcript'.")
    path = _save_upload(audio) if audio is not None else None
    ref = _save_upload(reference_audio) if reference_audio else None
    try:
        voice, identity, intent, risk = _run_pipeline(path, transcript, ref, claimed_identity)
        case_id = new_case_id()
        report = build_report(
            case_id, utc_now(), _sha256_file(path) if path else None,
            voice.model_dump() if voice else None,
            identity.model_dump() if identity else None,
            intent.model_dump() if intent else None,
            risk.model_dump(),
        )
        pdf = render_pdf(report)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{case_id}.pdf"'},
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if path:
            os.unlink(path)
        if ref:
            os.unlink(ref)


# ---- Voiceprint registry (Check 2 setup) ----

@app.post("/api/voices/register")
async def register_voice(name: str = Form(...), audio: UploadFile = File(...)):
    v = _get_verifier()
    if v is None:
        raise HTTPException(status_code=503, detail=f"Needs speechbrain: {_verifier_error}")
    path = _save_upload(audio)
    try:
        registry.save_voiceprint(name, v.embedding_list(path))
    finally:
        os.unlink(path)
    return {"registered": name}


@app.get("/api/voices")
def list_voices():
    return {"voices": registry.list_voiceprints()}


@app.delete("/api/voices/{name}")
def delete_voice(name: str):
    if not registry.delete_voiceprint(name):
        raise HTTPException(status_code=404, detail=f"'{name}' is not registered.")
    return {"deleted": name}
