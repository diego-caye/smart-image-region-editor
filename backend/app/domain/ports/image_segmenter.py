from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.entities.region import DetectedRegion
from app.domain.value_objects.mask_scope import MaskScope


@dataclass(slots=True)
class SegmentationResult:
    """A precise, single-channel mask, full-size (same dimensions as the
    image it was produced from) so downstream ports never need crop-offset
    math to use it."""

    mask_png_bytes: bytes
    width: int
    height: int


class ImageSegmenter(ABC):
    """Produces a precise, pixel-level mask for a previously detected
    region — all of it, or only its innermost visible layer (MaskScope)."""

    @abstractmethod
    def segment(
        self,
        image_bytes: bytes,
        region: DetectedRegion,
        *,
        scope: MaskScope = MaskScope.WHOLE_REGION,
    ) -> SegmentationResult: ...
