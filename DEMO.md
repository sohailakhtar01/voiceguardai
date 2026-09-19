# VoiceGuard AI — Demo Kit (SIH26104)

Everything you need to present confidently. Lead with what's rock-solid (**Upload**),
be honest about the hard parts (that honesty *impresses* judges).

---

## 0. Start the app (2 terminals)

**Terminal 1 — backend:**
```
cd voiceguardai/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Wait for `Application startup complete`. Check the badge later says **live model**.

**Terminal 2 — frontend:**
```
cd voiceguardai
npm run dev
```
Open **http://localhost:3000**. Top-right badge should read **"live model"** (green).

---

## 1. The 30-second pitch

> "Voice-cloning scams are exploding in India. VoiceGuard AI tells you whether a voice
> clip is **real or AI-generated** — and *where* in the clip the AI is, second by second.
> We trained **our own** model on the ASVspoof benchmark and then fine-tuned it on
> **Indian speech (Hindi + Indian English)** so it works for our users, not just Western
> English. It runs **fully offline, at zero cost**, and reads any format — even WhatsApp voice notes."

---

## 2. Demo order (what to click, what to expect)

Do these **in this order**. Use **Upload** for the reliable wow moments.

| # | Do this | Expected | Say this |
|---|---|---|---|
| 1 | **Upload an AI voice file** (ElevenLabs/ChatGPT audio saved as mp3/m4a) | **AI-generated**, high % | "Real synthetic audio — caught." |
| 2 | **Upload a real human clip** (record on phone, send to laptop) | **Real human voice** | "And it doesn't cry wolf on genuine voices." |
| 3 | **Upload a mixed clip** (AI + human stitched) | **Partly AI** + red/green **timeline** | "It localises *which seconds* are fake — not just yes/no." |
| 4 | **Upload a WhatsApp voice note** (.opus/.m4a) | analyses fine | "Works on real-world formats people actually use." |
| 5 | Point at the **timeline + gauge + verdict** | — | "Explainable: we show the evidence, not a black-box score." |

**Golden rule:** for AI clips, **Upload the file** — do NOT play it through a speaker and
record it (see Limitations).

---

## 3. Honest metrics you can claim

- ✅ "We **trained our own model** (wav2vec2), not an off-the-shelf API."
- ✅ "**EER 0.05% on the ASVspoof 2019 LA benchmark**" — *say "benchmark," never "real-world."*
- ✅ "Fine-tuned on **AI4Bharat** Indian speech (Hindi + Indian-accented English) with
  **augmentation** (noise, compression) so it survives real recording conditions."
- ✅ "Runs **offline, ₹0**, on CPU. Audio is processed locally and deleted — nothing uploaded."

**Do NOT say:** "99% accurate in the real world." (It's an in-domain benchmark number.)

---

## 4. Known limitations — frame them as sophistication

Judges respect teams who know their system's edges.

- **Live mic in a noisy room / replay attacks** (playing a fake through a speaker and
  re-recording): harder, because re-recording adds real-room acoustics that mask the AI
  fingerprint. *"This is a known research problem called replay/laundering; our roadmap
  adds replay-augmented training to close it."*
- **Accent generalisation:** English deepfake detection is strongest; Indian-language
  coverage is our active work (we already fine-tuned on AI4Bharat — this is a direction,
  not a finished claim).
- **It's probabilistic, not proof** — we present it as decision *support*, with evidence.

---

## 5. Why we're different (the SIH angle)

1. **India-first** — fine-tuned on Indian speech, handles Hindi + Indian English.
2. **Explainable** — per-second timeline showing *where* the AI is, not just a score.
3. **Honest** — we report in-domain benchmark numbers and name our limitations.
4. **Zero-cost & offline** — no paid APIs, runs on a laptop, privacy-preserving.
5. **Real-world ready** — accepts WhatsApp/phone formats out of the box.

---

## 6. If something breaks (fallbacks)

- **Badge says "offline"** → backend isn't running. Start Terminal 1.
- **Badge says "demo engine"** → `.env` isn't set to `wav2vec2`; restart backend.
- **A clip errors** → try a different file; upload a WAV/MP3 as a safe fallback.
- **Have 2–3 pre-tested clips saved locally** (one AI, one real, one mixed) so you're never
  live-recording on stage.

---

*Model: `voiceguard-india` · Engine: wav2vec2 · Runs locally.*
