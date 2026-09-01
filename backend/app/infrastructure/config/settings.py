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

    # --- ComfyUI (Infrastructure/image_editing/comfyui) ---
    comfyui_base_url: str = "http://127.0.0.1:8188"
    comfyui_poll_interval_seconds: float = 1.0
    comfyui_timeout_seconds: float = 180.0

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
