from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Single source of env-driven configuration. Nothing outside
    infrastructure/ should read an environment variable directly — go
    through this instead."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Storage ---
    storage_root: Path = BACKEND_ROOT / "data" / "images"
    static_url_prefix: str = "/static"

    # --- Database (SQLite for the MVP; swap to a Postgres URL later —
    # nothing else in the app needs to change, only this setting and the
    # adapter's engine construction). ---
    database_url: str = f"sqlite:///{BACKEND_ROOT / 'data' / 'app.db'}"

    # --- CORS (the Vite dev server). 5180, not 5173: the default 5173 is
    # already used by another project on this machine. ---
    cors_allow_origins: list[str] = ["http://localhost:5180", "http://127.0.0.1:5180"]

    # --- ComfyUI (infrastructure/image_editing/comfyui) ---
    comfyui_base_url: str = "http://127.0.0.1:8188"
    comfyui_poll_interval_seconds: float = 1.0
    comfyui_timeout_seconds: float = 180.0

    # Qwen Image Edit model files + sampling params — verified against the
    # real local ComfyUI's /object_info and confirmed working end-to-end
    # (see docs/architecture.md). Configurable here, not hardcoded in the
    # adapter, so swapping models/settings never touches Application code.
    qwen_unet_name: str = "qwen_image_edit_2511_fp8mixed.safetensors"
    qwen_clip_name: str = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
    qwen_vae_name: str = "qwen_image_vae.safetensors"
    qwen_lora_name: str = "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
    qwen_lora_strength: float = 1.0
    qwen_model_shift: float = 3.1
    qwen_cfg_norm_strength: float = 1.0
    qwen_steps: int = 4
    qwen_cfg: float = 1.0
    qwen_sampler_name: str = "euler"
    qwen_scheduler: str = "simple"

    # How much extra surrounding context to include when cropping a region
    # for editing (pixels on each side) — gives Qwen enough of the hand/face
    # to work with instead of an edge-to-edge crop. 100px matched the probe
    # that validated this workflow.
    edit_crop_context_margin_px: int = 100

    # --- Detection/segmentation device placement (backend's own ML stack;
    # shares one GPU with ComfyUI — see docs/architecture.md). ---
    detection_device: str = "cpu"  # YOLOv8n face/hand: tiny, fast, no VRAM impact
    segmentation_device: str = "cuda"  # SAM2: quality benefits from GPU, released after each call

    # Reuse ComfyUI's already-downloaded YOLO weights by default instead of
    # duplicating the download; override via env if you'd rather keep a
    # private copy under the backend's own models_cache/.
    yolo_face_model_path: Path = Path("C:/ComfyUI/models/ultralytics/bbox/face_yolov8n.pt")
    yolo_hand_model_path: Path = Path("C:/ComfyUI/models/ultralytics/bbox/hand_yolov8n.pt")

    # SAM2's official pip package needs its own checkpoint format — not the
    # safetensors ComfyUI's custom node uses — so the backend fetches/caches
    # its own copy here on first use.
    sam2_model_id: str = "facebook/sam2-hiera-base-plus"
    models_cache_dir: Path = BACKEND_ROOT / "models_cache"


@lru_cache
def get_settings() -> Settings:
    return Settings()
