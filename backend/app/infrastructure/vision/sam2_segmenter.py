"""Thin wrapper around Meta's SAM2 image predictor. Verified against the
real installed `sam2` package's API (sam2/sam2_image_predictor.py and
sam2/build_sam.py) rather than assumed — same discipline as the ComfyUI
client.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from app.infrastructure.vision.device import release_cuda_memory


class Sam2MaskPredictor:
    """Produces a full-size binary mask from a bounding-box prompt. Rebuilt
    and released on every call rather than kept resident: SAM2 is the
    heaviest model the backend loads on its own, and releasing it after
    each call frees VRAM for ComfyUI's Qwen edit step later in the flow —
    see docs/architecture.md."""

    def __init__(self, model_id: str, *, device: str, cache_dir: Path) -> None:
        self._model_id = model_id
        self._device = device
        # sam2's checkpoint download goes through huggingface_hub, which
        # only reads its cache location from the HF_HOME env var — there is
        # no cache_dir kwarg threaded through build_sam2_hf/from_pretrained.
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(cache_dir))

    def segment_box(self, image_rgb: np.ndarray, box_xyxy: tuple[int, int, int, int]) -> np.ndarray:
        from sam2.sam2_image_predictor import SAM2ImagePredictor

        predictor = SAM2ImagePredictor.from_pretrained(self._model_id, device=self._device)
        try:
            predictor.set_image(image_rgb)
            masks, _scores, _low_res_logits = predictor.predict(
                box=np.array(box_xyxy, dtype=np.float32),
                multimask_output=False,
            )
            return masks[0] > 0.5
        finally:
            del predictor
            release_cuda_memory()
