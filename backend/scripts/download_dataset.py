"""Download ASVspoof 2019 — our training dataset (Phase 5).

Run once, when ready to train:
    pip install kagglehub
    # put your free Kaggle token at ~/.kaggle/kaggle.json  (Kaggle > Account > Create New API Token)
    python scripts/download_dataset.py

Note: this is a multi-GB download. Do it on a machine with space
(or run training on Kaggle/Colab where the data is already local).
"""

import kagglehub

if __name__ == "__main__":
    path = kagglehub.dataset_download("awsaf49/asvpoof-2019-dataset")
    print("ASVspoof 2019 downloaded to:", path)
