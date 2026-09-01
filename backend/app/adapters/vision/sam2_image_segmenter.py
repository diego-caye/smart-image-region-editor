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
from app.infrastructure.vision.sam2_segmenter import Sam2MaskPredictor


class Sam2ImageSegmenter(ImageSegmenter):
    def __init__(self, predictor: Sam2MaskPredictor) -> None:
        self._predictor = predictor

    def segment(self, image_bytes: bytes, region: DetectedRegion) -> SegmentationResult:
        image = PILImage.open(BytesIO(image_bytes)).convert("RGB")
        image_rgb = np.array(image)

        mask = self._predictor.segment_box(image_rgb, region.bounding_box.as_xyxy())

        mask_image = PILImage.fromarray(mask.astype(np.uint8) * 255, mode="L")
        buffer = BytesIO()
        mask_image.save(buffer, format="PNG")

        return SegmentationResult(
            mask_png_bytes=buffer.getvalue(), width=image.width, height=image.height
        )
