# VoiceGuard AI — Training (Phase 5)

Trains our own real/fake voice model, including the **India-first** edge.
Do this on a **free GPU** (Google Colab / Kaggle) — it's too slow CPU-only.

## Steps

1. **Get the base dataset** (ASVspoof 2019):
   ```bash
   pip install kagglehub
   python scripts/download_dataset.py         # prints a path
   python ml/prepare_asvspoof.py --root <that-path> --out ml/data
   ```

2. **Build the India edge** (our differentiator):
   ```bash
   pip install edge-tts
   # download Common Voice 'hi' (CC0) first, note its clips/ folder
   python ml/generate_indian_data.py --real-dir <common_voice_hi/clips> --out ml/data_india
   # then append india.csv to train.csv so the model learns Indian voices
   ```

3. **Train** (on GPU):
   ```bash
   pip install -r requirements-ml.txt
   python ml/train.py --manifest ml/data/train.csv --val ml/data/val.csv \
       --out models/vgai-wav2vec2 --epochs 3 --freeze-encoder
   ```

4. **Use it in the app** — set in `backend/.env`:
   ```
   DETECTOR_ENGINE=wav2vec2
   WAV2VEC2_MODEL=./models/vgai-wav2vec2
   ```

## Honest notes
- These scripts are written but **not yet run** (no GPU in the build session) —
  expect to tweak dataset folder names to match your download.
- Report **real** accuracy / false-positive numbers from the eval set. Never a fake "99%".
- Anti-overfitting: multiple TTS voices for fakes + `--freeze-encoder` + augmentation.
