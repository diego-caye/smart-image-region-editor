# Plain python:3.12-slim, not an nvidia/cuda base image: PyTorch's cu130
# wheels bundle their own CUDA runtime libraries as pip dependencies, so all
# that's needed from the host is the NVIDIA driver + container toolkit
# exposing the GPU (docker-compose.yml's `deploy.resources.reservations`).
FROM python:3.12-slim

# libgl1/libglib2.0-0: transitively needed by opencv-python-headless
# (pulled in by ultralytics) for image decoding. libegl1/libgles2:
# mediapipe's compiled Tasks API bindings dlopen() libEGL.so.1 and then
# libGLESv2.so.2 at import time even for CPU-only inference (confirmed one
# at a time by the real OSError without each) — no GPU/display involved,
# just hard runtime dependencies of the wheel.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libegl1 \
    libgles2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app

# Order matters: torch/torchvision are installed FIRST, pinned to the exact
# build ComfyUI itself uses (cu130, verified against this project's RTX
# 5080/Blackwell GPU — see docs/architecture.md). Installing them first
# means ultralytics/sam2's own (unpinned) torch dependency is already
# satisfied and pip won't silently replace this build with a CPU-only or
# differently-CUDA'd one from PyPI's default index.
RUN pip install --no-cache-dir "torch==2.10.0+cu130" "torchvision==0.25.0+cu130" \
      --index-url https://download.pytorch.org/whl/cu130 \
 && pip install --no-cache-dir -e ".[dev,ml]"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
