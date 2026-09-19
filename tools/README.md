# tools/ — demo utilities (NOT part of the app)

These are throwaway helpers for preparing demos. They are **not** imported by the
backend or frontend, and are **never** deployed.

## clone_voice.ipynb
Makes a fake AI clone of a voice (XTTS-v2) so you can test the detector.

**Run it on Google Colab** (needs a free GPU):
1. Go to **colab.research.google.com** → **File → Upload notebook** → pick `clone_voice.ipynb`.
2. **Runtime → Change runtime type → T4 GPU**.
3. Run the cells top to bottom: install → upload a real voice clip → edit the text → clone → download `cloned.wav`.
4. Upload `cloned.wav` into the VoiceGuard app to demo detection.

⚠️ Clone only a voice you have consent for (e.g. your own family member, for this demo).
The cloning library (~2 GB) stays on Colab — it is intentionally kept out of the app.
