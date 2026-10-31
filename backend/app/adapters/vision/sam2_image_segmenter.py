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


class Sam2ImageSegmenter(ImageSegmenter):
    def __init__(self, predictor: Sam2MaskPredictor) -> None:
        self._predictor = predictor

    def segment(self, image_bytes: bytes, region: DetectedRegion) -> SegmentationResult:
        image = PILImage.open(BytesIO(image_bytes)).convert("RGB")
        image_rgb = np.array(image)

        also_point = (
            region.bounding_box.center
            if region.region_type in _LAYERED_CLOTHING_REGIONS
            else None
        )
        mask = self._predictor.segment_box(
            image_rgb, region.bounding_box.as_xyxy(), also_point_xy=also_point
        )

        mask_image = PILImage.fromarray(mask.astype(np.uint8) * 255, mode="L")
        buffer = BytesIO()
        mask_image.save(buffer, format="PNG")

        return SegmentationResult(
            mask_png_bytes=buffer.getvalue(), width=image.width, height=image.height
        )
