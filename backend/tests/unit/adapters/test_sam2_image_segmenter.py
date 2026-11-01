"""Which SAM2 prompts the adapter sends per region type, with a stub in
place of Sam2MaskPredictor — no torch, no checkpoint."""

from __future__ import annotations

import io
from uuid import uuid4

import numpy as np
from PIL import Image

from app.adapters.vision.sam2_image_segmenter import Sam2ImageSegmenter, strip_above
from app.domain.entities.region import DetectedRegion
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.mask_scope import MaskScope
from app.domain.value_objects.region_type import RegionType


class StubPredictor:
    """segment_box returns the outer layer (a jacket: columns 40-70 and
    130-160 of the box); segment_point the inner one (a shirt: columns
    70-130, rows 60-180), unless told the point hit something tiny."""

    def __init__(self, *, tiny_point_mask: bool = False) -> None:
        self.calls: list[tuple] = []
        self._tiny = tiny_point_mask

    def segment_box(self, image_rgb, box_xyxy, *, also_point_xy=None):
        self.calls.append((box_xyxy, also_point_xy))
        mask = np.zeros(image_rgb.shape[:2], dtype=bool)
        mask[20:180, 40:70] = mask[20:180, 130:160] = True
        return mask

    def segment_point(self, image_rgb, point_xy):
        self.calls.append(("point", point_xy))
        mask = np.zeros(image_rgb.shape[:2], dtype=bool)
        if self._tiny:
            mask[98:102, 98:102] = True
        else:
            mask[60:180, 70:130] = True
        return mask


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


def _mask_of(result) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(result.mask_png_bytes))) > 0


def test_inner_layer_is_the_shirt_plus_room_above_its_neckline_never_the_jacket():
    predictor = StubPredictor()
    result = Sam2ImageSegmenter(predictor).segment(
        _png(), _region(RegionType.TORSO), scope=MaskScope.INNER_LAYER
    )
    mask = _mask_of(result)
    assert mask[60:180, 70:130].all()  # the shirt
    assert mask[44:60, 70:130].all()  # 10% of the 160px box above the neckline
    assert not mask[:43, :].any()
    assert not mask[:, 40:70].any() and not mask[:, 130:160].any()  # the jacket


def test_inner_layer_falls_back_to_the_whole_region_when_the_point_hits_a_detail():
    predictor = StubPredictor(tiny_point_mask=True)
    Sam2ImageSegmenter(predictor).segment(
        _png(), _region(RegionType.TORSO), scope=MaskScope.INNER_LAYER
    )
    assert predictor.calls[-1] == ((40, 20, 160, 180), (100.0, 100.0))


def test_strip_above_follows_each_column_top_edge():
    mask = np.zeros((10, 3), dtype=bool)
    mask[5:, 0] = True
    mask[3:, 1] = True
    strip = strip_above(mask, 2)
    assert strip[:, 0].tolist() == [False] * 3 + [True] * 2 + [False] * 5
    assert strip[:, 1].tolist() == [False] + [True] * 2 + [False] * 7
    assert not strip[:, 2].any()

