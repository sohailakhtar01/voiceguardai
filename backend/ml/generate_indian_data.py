"""Phase 5 DIFFERENTIATOR — build a small Indian-language fake/real set.

FAKE voices: synthesized with edge-tts using MULTIPLE Indian neural voices
(using several TTS voices stops the model just learning one TTS fingerprint).
REAL voices: Mozilla Common Voice 'hi' clips (CC0) — download separately and
pass the clips folder via --real-dir.

    pip install edge-tts
    python ml/generate_indian_data.py --out ml/data_india --real-dir <common_voice_hi/clips>

Output: ml/data_india/india.csv  (path,label ; 0=real, 1=fake)
This is what makes VoiceGuard different from every English-only attempt.
"""

import argparse
import asyncio
import csv
from pathlib import Path

# Several Indian voices on purpose (anti-overfitting to one TTS).
HINDI_VOICES = [
    "hi-IN-SwaraNeural",
    "hi-IN-MadhurNeural",
    "en-IN-NeerjaNeural",
    "en-IN-PrabhatNeural",
]

# Mix of scam + benign, code-mixed like real Indian calls.
PHRASES = [
    "Sir turant OTP batao aur paise transfer karo",
    "main bank se bol raha hoon, account verify karna hai",
    "jaldi karo, emergency hai, paise bhejo",
    "aapka KYC update karna hai, OTP share kijiye",
    "namaste, kal lunch ke liye milte hain",
    "project ka update kal bhej dena",
]


async def _synth(text: str, voice: str, out_path: Path) -> None:
    import edge_tts

    await edge_tts.Communicate(text, voice).save(str(out_path))


async def make_fakes(out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, i = [], 0
    for voice in HINDI_VOICES:
        for text in PHRASES:
            p = out_dir / f"fake_{i:04d}.mp3"
            await _synth(text, voice, p)
            rows.append({"path": str(p), "label": 1})
            i += 1
    return rows


def collect_reals(real_dir: Path | None, limit: int = 200) -> list[dict]:
    rows = []
    if real_dir and real_dir.exists():
        clips = list(real_dir.glob("*.mp3"))[:limit] + list(real_dir.glob("*.wav"))[:limit]
        rows = [{"path": str(p), "label": 0} for p in clips]
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="ml/data_india")
    ap.add_argument("--real-dir", default="")
    args = ap.parse_args()

    out = Path(args.out)
    fakes = asyncio.run(make_fakes(out / "fakes"))
    reals = collect_reals(Path(args.real_dir) if args.real_dir else None)

    manifest = out / "india.csv"
    with open(manifest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "label"])
        w.writeheader()
        w.writerows(fakes + reals)

    print(f"India set: {len(fakes)} fake + {len(reals)} real -> {manifest}")
    if not reals:
        print("NOTE: no real clips found — download Common Voice 'hi' and pass --real-dir.")


if __name__ == "__main__":
    main()
