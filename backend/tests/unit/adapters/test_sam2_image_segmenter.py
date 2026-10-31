"""Which SAM2 prompts the adapter sends per region type, with a stub in
place of Sam2MaskPredictor — no torch, no checkpoint."""

from __future__ import annotations

import io
from uuid import uuid4

import numpy as np
from PIL import Image

from app.adapters.vision.sam2_image_segmenter import Sam2ImageSegmenter
from app.domain.entities.region import DetectedRegion
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.region_type import RegionType


class StubPredictor:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def segment_box(self, image_rgb, box_xyxy, *, also_point_xy=None):
        self.calls.append((box_xyxy, also_point_xy))
        return np.zeros(image_rgb.shape[:2], dtype=bool)


def _png(width=200, height=200) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


def _region(region_type: RegionType) -> DetectedRegion:
    return DetectedRegion.new(
        image_id=uuid4(),
        region_type=region_type,
        bounding_box=BoundingBox(x_min=40, y_min=20, x_max=160, y_max=180),
        confidence=0.9,
    )


def test_torso_also_segments_the_box_center_to_catch_the_inner_layer():
    predictor = StubPredictor()
    Sam2ImageSegmenter(predictor).segment(_png(), _region(RegionType.TORSO))
    assert predictor.calls == [((40, 20, 160, 180), (100.0, 100.0))]


def test_other_regions_are_box_only():
    # a point at the center of legs/arms boxes usually lands on background
    for region_type in (RegionType.LEGS, RegionType.RIGHT_ARM, RegionType.RIGHT_HAND):
        predictor = StubPredictor()
        Sam2ImageSegmenter(predictor).segment(_png(), _region(region_type))
        assert predictor.calls == [((40, 20, 160, 180), None)]
