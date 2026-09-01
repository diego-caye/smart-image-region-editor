from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def resolve_device(requested: str) -> str:
    """Resolve a configured device string ("cpu"/"cuda") to one actually
    usable on this machine, falling back to CPU with a warning rather than
    crashing — e.g. torch not installed, or installed without support for
    this GPU's compute capability."""
    if requested != "cuda":
        return "cpu"

    try:
        import torch
    except ImportError:
        logger.warning("torch is not installed; falling back to CPU for detection/segmentation")
        return "cpu"

    if not torch.cuda.is_available():
        logger.warning("CUDA requested but not available; falling back to CPU")
        return "cpu"

    return "cuda"


def release_cuda_memory() -> None:
    """Called after a detection/segmentation pass so VRAM is free for
    ComfyUI's (much larger) Qwen edit step — see docs/architecture.md."""
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass
