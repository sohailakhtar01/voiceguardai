"""Phase 5 — fine-tune wav2vec2 for real/fake voice detection.

RUN ON A GPU (Google Colab / Kaggle). Not tested on a CPU-only laptop.

    python ml/train.py --manifest ml/data/train.csv --val ml/data/val.csv \
        --out models/vgai-wav2vec2 --epochs 3 --freeze-encoder

Manifest CSV columns: path,label   (0 = real, 1 = fake).
To add the India edge, concatenate ml/data/train.csv + ml/data_india/india.csv.
After training, point the backend at it: WAV2VEC2_MODEL=./models/vgai-wav2vec2
"""

import argparse
import csv

import numpy as np
import torch
from torch.utils.data import Dataset
from transformers import (
    AutoFeatureExtractor,
    AutoModelForAudioClassification,
    Trainer,
    TrainingArguments,
)

SR = 16000
MAX = 64000  # 4 seconds


def load_wav(path: str):
    try:
        import soundfile as sf

        wav, sr = sf.read(path, dtype="float32", always_2d=True)
        wav = wav.mean(axis=1)
    except Exception:
        import librosa

        wav, sr = librosa.load(path, sr=SR, mono=True)
    if sr != SR:
        import librosa

        wav = librosa.resample(wav, orig_sr=sr, target_sr=SR)
    return wav[:MAX]


class AudioCSV(Dataset):
    def __init__(self, manifest: str):
        with open(manifest, encoding="utf-8") as f:
            self.rows = list(csv.DictReader(f))

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        return {"wav": load_wav(r["path"]), "labels": int(r["label"])}


class Collator:
    def __init__(self, extractor):
        self.extractor = extractor

    def __call__(self, batch):
        feats = self.extractor(
            [b["wav"] for b in batch],
            sampling_rate=SR,
            padding=True,
            max_length=MAX,
            truncation=True,
            return_tensors="pt",
        )
        feats["labels"] = torch.tensor([b["labels"] for b in batch])
        return feats


def compute_metrics(p):
    preds = np.argmax(p.predictions, axis=1)
    return {"accuracy": float((preds == p.label_ids).mean())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--base", default="facebook/wav2vec2-base")
    ap.add_argument("--out", default="models/vgai-wav2vec2")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--freeze-encoder", action="store_true")
    args = ap.parse_args()

    extractor = AutoFeatureExtractor.from_pretrained(args.base)
    model = AutoModelForAudioClassification.from_pretrained(
        args.base,
        num_labels=2,
        label2id={"real": 0, "fake": 1},
        id2label={0: "real", 1: "fake"},
    )
    if args.freeze_encoder and hasattr(model, "freeze_feature_encoder"):
        model.freeze_feature_encoder()  # keep low-level acoustics, train the head

    targs = TrainingArguments(
        output_dir=args.out,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=args.batch,
        num_train_epochs=args.epochs,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=1e-4,
        logging_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        fp16=torch.cuda.is_available(),
    )

    trainer = Trainer(
        model=model,
        args=targs,
        train_dataset=AudioCSV(args.manifest),
        eval_dataset=AudioCSV(args.val),
        data_collator=Collator(extractor),
        compute_metrics=compute_metrics,
    )
    trainer.train()
    trainer.save_model(args.out)
    extractor.save_pretrained(args.out)
    print("Saved fine-tuned model to", args.out)


if __name__ == "__main__":
    main()
