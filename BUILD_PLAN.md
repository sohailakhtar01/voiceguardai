# VoiceGuard AI — Build Plan (SIH26104)

Frontend = Next.js (this repo root) · Backend = Python FastAPI (`/backend`) · DB = Supabase.
Strategy: **get a working demo first, then make it smarter.** You're never stuck with nothing to show.

## How to run what exists (Phase 1a — DONE ✅)
```bash
cd backend
pip install -r requirements.txt          # light, no ML
uvicorn app.main:app --reload            # API at http://localhost:8000/docs
pytest -q                                # 2 tests pass
```
Right now the API answers `/health` and `POST /api/analyze/voice` using the **mock** engine
(deterministic, no ML) — so the app is fully buildable before the AI model is installed.

## Phases

| Phase | What | Status | Who runs the heavy bit |
|---|---|---|---|
| 0. Scaffold + git | project structure, config, tests | ✅ done | — |
| 1a. Mock detector API | runnable API + tests | ✅ done | — |
| 1b. Real detector | swap in pretrained wav2vec2 | ⏳ needs you | you: `pip install -r requirements-ml.txt`, set `DETECTOR_ENGINE=wav2vec2` |
| 2. Check 2 — identity | speaker verification (voiceprint) | ✅ code ready | lights up after `speechbrain` install |
| 3. Check 3 — intent | speech-to-text + Hindi scam words | ✅ done + tested | — (Hindi text works now) |
| 4. Risk engine + "why" | combine checks + evidence + Supabase store | ✅ done + tested | Supabase gated on your keys |
| 5. India edge | Hindi + Tamil/Telugu/Kannada/Bengali/Marathi detection; fine-tune scripts | ✅ 6 languages live; scripts written | **you: run training on free Colab/Kaggle GPU** |
| 6. Near-real-time | mic capture in dashboard | ✅ mic record wired | full streaming later |
| 7. Frontend + report | dashboard + evidence + PDF/JSON report + identity input | ✅ done, build passes | — |

**Extras done:** forensic report (PDF+JSON) · voiceprint registry API · Supabase persistence (gated) · model-verify script · real README. Backend **18/18 tests pass**.

## Honest division of labour
- **Claude writes every line of code** + debugs with you.
- **You** press run, install the ML libs when prompted, start the **free Colab training** (no GPU in chat), and record demo clips.
- **Nobody can** guarantee perfect accuracy on every unseen fake — Phase 4 reports honest numbers.

## Parallel agents — when
Phases 0–1 are foundation (shared files) → built directly, in order, to avoid collisions.
Phases 2, 3 are **independent modules** → these get built by **parallel agents**, one per module.

## Dataset
- Train: **ASVspoof 2019** — `backend/scripts/download_dataset.py` (Kaggle `awsaf49/asvpoof-2019-dataset`)
- Test/generalization: ASVspoof 2021 DF eval (friend's Zenodo link) + In-the-Wild
- India edge (we auto-generate): Common Voice Hindi (real) + multi-TTS fakes
