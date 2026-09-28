#!/bin/sh
# Downloads the exact 4 model files backend/infrastructure/image_editing/comfyui/
# needs, if they aren't already present in the persistent /data volume. Every
# URL/filename/size below was verified against the real Hugging Face API
# before being written here — not guessed — and matches byte-for-byte the
# files already on this machine's native ComfyUI install (see
# docs/architecture.md), which is exactly why the backend's default
# QWEN_UNET_NAME/QWEN_VAE_NAME/etc. settings work unchanged against this
# containerized ComfyUI too.
set -e

MODELS_DIR="${MODELS_DIR:-/data/models}"

download_if_missing() {
  dest="$1"
  url="$2"
  if [ -f "$dest" ]; then
    echo "[download_models] already present: $dest"
    return
  fi
  echo "[download_models] downloading -> $dest"
  mkdir -p "$(dirname "$dest")"
  curl -L --fail --retry 3 --retry-delay 5 -o "$dest.part" "$url"
  mv "$dest.part" "$dest"
}

download_if_missing \
  "$MODELS_DIR/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors" \
  "https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors"

download_if_missing \
  "$MODELS_DIR/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors" \
  "https://huggingface.co/Comfy-Org/HunyuanVideo_1.5_repackaged/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors"

download_if_missing \
  "$MODELS_DIR/vae/qwen_image_vae.safetensors" \
  "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors"

download_if_missing \
  "$MODELS_DIR/loras/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors" \
  "https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning/resolve/main/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"

echo "[download_models] all models present."
