# Vanilla ComfyUI — no custom_nodes. Our workflow
# (backend/app/infrastructure/image_editing/comfyui/workflows/qwen_edit.json)
# was checked node-by-node against the real ComfyUI source: every class it
# uses (LoadImage, UNETLoader, CLIPLoader, VAELoader, ModelSamplingAuraFlow,
# CFGNorm, LoraLoaderModelOnly, TextEncodeQwenImageEditPlus,
# FluxKontextMultiReferenceLatentMethod, FluxKontextImageScale, VAEEncode,
# KSampler, VAEDecode, SaveImage) lives in nodes.py/comfy_extras/ — none of
# them are provided by a custom_nodes package. That means we don't need to
# containerize the whole custom-node ecosystem a desktop ComfyUI
# accumulates over time (Impact Pack, KJ nodes, etc.) — reusing the graph
# and the model *files* is enough, exactly as intended: a clean checkout
# plus the 4 model files this workflow needs.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/comfyui

# Pinned to a real, verified release tag (github.com/comfyanonymous/ComfyUI,
# confirmed via the GitHub releases API — not guessed).
RUN git clone --branch v0.37.0 --depth 1 https://github.com/comfyanonymous/ComfyUI.git .

# Same cu130 pin as backend/Dockerfile — matches the exact PyTorch build
# ComfyUI's own desktop app uses on this RTX 5080 (Blackwell); a plain
# `pip install torch` would resolve a build without support for this GPU.
RUN pip install --no-cache-dir "torch==2.10.0+cu130" "torchvision==0.25.0+cu130" "torchaudio==2.10.0+cu130" \
      --index-url https://download.pytorch.org/whl/cu130 \
 && pip install --no-cache-dir -r requirements.txt

COPY download_models.sh entrypoint.sh /opt/comfyui/
RUN chmod +x /opt/comfyui/download_models.sh /opt/comfyui/entrypoint.sh

EXPOSE 8188

ENTRYPOINT ["/opt/comfyui/entrypoint.sh"]
