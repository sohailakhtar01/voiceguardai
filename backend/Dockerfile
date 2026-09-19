FROM python:3.12-slim

WORKDIR /app

# System deps: ffmpeg fallback (imageio-ffmpeg bundles its own binary, but
# libsndfile is needed by soundfile for WAV/FLAC decoding).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-ml.txt ./
# CPU-only torch/torchaudio first — the default PyPI wheels drag in several GB
# of NVIDIA CUDA libraries (cudnn, cublas, nccl, ...) this container never
# uses since there's no GPU passthrough here. Installing the CPU build first
# satisfies requirements-ml.txt's "torch>=2.2" so pip won't pull the GPU one.
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt -r requirements-ml.txt

COPY app ./app
COPY models ./models

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
