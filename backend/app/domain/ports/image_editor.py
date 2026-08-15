from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.edit_operation import EditOperation


@dataclass(slots=True)
class EditResult:
    """The raw output of a localized edit, plus whatever metadata is worth
    keeping for reproducibility (seed, model/workflow identifiers)."""

    edited_region_png_bytes: bytes
    region_box_used: BoundingBox
    seed: int | None
    model_metadata: dict


class ImageEditor(ABC):
    """Performs one localized, structured edit of a region. Implementations
    own every detail of *how* (which model, which prompt, which server) —
    Application only knows this contract. Nothing here mentions ComfyUI or
    Qwen; see infrastructure/image_editing/comfyui for that.
    """

    @abstractmethod
    def edit(
        self,
        *,
        image_png_bytes: bytes,
        mask_png_bytes: bytes,
        region_box: BoundingBox,
        operation: EditOperation,
        reference_image_png_bytes: bytes | None = None,
    ) -> EditResult:
        """image_png_bytes/mask_png_bytes are full-size and share the same
        dimensions; region_box marks where the edit is requested.
        Implementations decide how much surrounding context to include when
        cropping for the underlying model, and report back the exact box the
        returned crop covers via region_box_used (it may be larger than
        region_box, but never smaller)."""
        ...
