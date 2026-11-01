"""Implements ImageSegmenter using SAM2, box-prompted from the region's
bounding box. Translation boundary between the raw numpy mask
infrastructure/vision/sam2_segmenter.py returns and Domain's
SegmentationResult (PNG bytes).
"""

from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image as PILImage

from app.domain.entities.region import DetectedRegion
from app.domain.ports.image_segmenter import ImageSegmenter, SegmentationResult
from app.domain.value_objects.mask_scope import MaskScope
from app.domain.value_objects.region_type import RegionType
from app.infrastructure.vision.sam2_segmenter import Sam2MaskPredictor

# SAM2 returns one object per prompt, and a box around a torso picks the
# most salient one — on someone wearing an open jacket, just the jacket. A
# garment edit ("red shirt") then can't touch the shirt underneath: found on
# a real photo, where the box-only mask covered 49% of the torso box and the
# edited shirt came out with the original black showing through its middle.
# Also segmenting a point at the box center (the chest, i.e. whatever is
# worn innermost) and taking the union covered jacket + shirt (74%) with no
# background. Not done for legs or arms: their box center usually falls on
# background (between the legs, beside a raised arm).
_LAYERED_CLOTHING_REGIONS = frozenset({RegionType.TORSO})

# For MaskScope.INNER_LAYER the point's mask alone is the inner garment: on
# the suit photo the box-only mask was the jacket with its sleeves (57% of
# the box) and the point added the T-shirt (24%). Without a jacket, the
# point's mask is the whole top, so nothing is lost. If the point lands on
# something tiny (a logo, a button), the edit would have almost nothing to
# change, so below this share of the box it falls back to the whole region.
_MIN_INNER_LAYER_BOX_FRACTION = 0.05

# The inner garment's own mask stops at its neckline, but a new top can
# rise above it: a hoodie's hood rests behind the neck. With the bare
# shirt mask, a real hoodie edit lost its hood (CLIP: hoodie 0.06 -> 0.15).
# So the inner-layer mask also gets a strip straight above the garment's
# top edge — this fraction of the region's height — minus the outer layer.
_NECK_STRIP_BOX_FRACTION = 0.1


class Sam2ImageSegmenter(ImageSegmenter):
    def __init__(self, predictor: Sam2MaskPredictor) -> None:
        self._predictor = predictor

    def segment(
        self,
        image_bytes: bytes,
        region: DetectedRegion,
        *,
        scope: MaskScope = MaskScope.WHOLE_REGION,
    ) -> SegmentationResult:
        image = PILImage.open(BytesIO(image_bytes)).convert("RGB")
        image_rgb = np.array(image)
        layered = region.region_type in _LAYERED_CLOTHING_REGIONS

        mask = None
        if scope is MaskScope.INNER_LAYER and layered:
            inner = self._predictor.segment_point(image_rgb, region.bounding_box.center)
            box_area = region.bounding_box.width * region.bounding_box.height
            if inner.sum() >= _MIN_INNER_LAYER_BOX_FRACTION * box_area:
                outer = self._predictor.segment_box(image_rgb, region.bounding_box.as_xyxy())
                strip_px = round(_NECK_STRIP_BOX_FRACTION * region.bounding_box.height)
                mask = inner | (strip_above(inner, strip_px) & ~outer)
        if mask is None:
            mask = self._predictor.segment_box(
                image_rgb,
                region.bounding_box.as_xyxy(),
                also_point_xy=region.bounding_box.center if layered else None,
            )

        mask_image = PILImage.fromarray(mask.astype(np.uint8) * 255, mode="L")
        buffer = BytesIO()
        mask_image.save(buffer, format="PNG")

        return SegmentationResult(
            mask_png_bytes=buffer.getvalue(), width=image.width, height=image.height
        )


def strip_above(mask: np.ndarray, height_px: int) -> np.ndarray:
    """In every column, the height_px pixels right above the mask's topmost
    pixel in that column."""
    strip = np.zeros_like(mask, dtype=bool)
    columns = np.flatnonzero(mask.any(axis=0))
    tops = mask[:, columns].argmax(axis=0)
    for column, top in zip(columns, tops, strict=True):
        strip[max(0, top - height_px) : top, column] = True
    return strip

