"""Phase 5 — build train/val CSV manifests from ASVspoof 2019 (LA).

Run after backend/scripts/download_dataset.py has fetched the data.
    python ml/prepare_asvspoof.py --root <path-printed-by-download_dataset> --out ml/data

Output CSV columns: path,label   (label: 0 = real/bonafide, 1 = fake/spoof)

NOTE: folder names can vary slightly between mirrors of this dataset. If a
path isn't found, `ls` the --root and adjust the names below to match.
"""

import argparse
import csv
from pathlib import Path


def build(protocol: Path, flac_dir: Path, out_csv: Path, split: str) -> None:
    rows = []
    if not protocol.exists():
        print(f"!! protocol not found: {protocol}")
        return
    with open(protocol, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 5:
                continue
            utt, key = parts[1], parts[4]
            path = flac_dir / f"{utt}.flac"
            if path.exists():
                rows.append({"path": str(path), "label": 0 if key == "bonafide" else 1})
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "label"])
        w.writeheader()
        w.writerows(rows)
    print(f"{split}: {len(rows)} clips -> {out_csv}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="ASVspoof2019 root (contains LA/)")
    ap.add_argument("--out", default="ml/data")
    args = ap.parse_args()

    la = Path(args.root) / "LA"
    proto = la / "ASVspoof2019_LA_cm_protocols"
    out = Path(args.out)
    build(proto / "ASVspoof2019.LA.cm.train.trn.txt",
          la / "ASVspoof2019_LA_train" / "flac", out / "train.csv", "train")
    build(proto / "ASVspoof2019.LA.cm.dev.trl.txt",
          la / "ASVspoof2019_LA_dev" / "flac", out / "val.csv", "val")


if __name__ == "__main__":
    main()
