# VoiceGuard AI 🛡️

**Real-time detection & prevention of voice-cloning impersonation attacks** — India-first, explainable.
Smart India Hackathon 2026 · Problem Statement **SIH26104** (AICTE Cyber Security Cell).

> When a voice can be faked, the interaction itself must be verified. VoiceGuard runs
> three checks on a call and returns one explainable risk score — and tells you *why*.

## What it does
1. **Fake voice?** — AI-clone / synthetic-audio detection (wav2vec2)
2. **Right person?** — speaker verification against a trusted voiceprint (ECAPA-TDNN)
3. **Scam intent?** — speech-to-text + scam-word detection in **Hindi, Tamil, Telugu, Kannada, Bengali, Marathi & code-mixed** speech

→ fused into a calibrated **risk score** (🟢 low → 🔴 critical) with **evidence** and an **adaptive response**, plus a downloadable **forensic report** (PDF/JSON).

## Structure
```
voiceguardai/
├── src/app/            Next.js dashboard (frontend)
└── backend/            Python FastAPI detection API
    ├── app/
    │   ├── detectors/  Check 1 — fake voice (mock | wav2vec2)
    │   ├── identity/   Check 2 — speaker verification + voiceprint registry
    │   ├── intent/     Check 3 — Hindi/code-mixed scam-intent
    │   ├── risk/       Layer 4 — explainable risk fusion
    │   └── report/     forensic report (JSON + PDF)
    ├── ml/             Phase 5 training (ASVspoof + India dataset)
    └── scripts/        dataset download, model verify
```

## Quickstart
**Backend** (runs immediately, no ML needed — uses a mock engine):
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload        # http://localhost:8000/docs
pytest -q                            # tests
```
**Frontend:**
```bash
npm install
npm run dev                          # http://localhost:3000
```
Open the dashboard, click the **🇮🇳 Hindi scam** example → **Analyze**.

## Turn on the real AI model
```bash
cd backend
pip install -r requirements-ml.txt   # ~2 GB (torch)
python scripts/verify_model.py       # confirm it loads
# then set in backend/.env:  DETECTOR_ENGINE=wav2vec2
```

## API
| Endpoint | Purpose |
|---|---|
| `POST /api/analyze/voice` | Check 1 only |
| `POST /api/analyze/intent` | Check 3 (`transcript` text or `audio`) |
| `POST /api/analyze/full` | full pipeline → risk + case metadata |
| `POST /api/report/pdf` | downloadable PDF forensic report |
| `POST /api/voices/register` · `GET /api/voices` · `DELETE /api/voices/{name}` | voiceprint registry |

## Honest notes
- The **India-language model** is trained separately on free GPU — see `backend/ml/README.md`.
- No detector is 100% on unseen fakes; we report **real** metrics, not a fake "99%".
- Free & open-source throughout; the whole demo runs locally at ₹0.

See [`BUILD_PLAN.md`](BUILD_PLAN.md) for the phase-by-phase status.
"# voiceguardai" 
