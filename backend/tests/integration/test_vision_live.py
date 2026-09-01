"""Opt-in tests against the REAL YOLOv8 + SAM2 models (not run by default —
see pyproject.toml's `addopts`). Run explicitly with:

    pytest -m live_models

Requires the `ml` extra installed (see backend/README.md) and the weight
files the default settings point at (ComfyUI's own face/hand YOLO weights)
to exist on disk. Manually verified once against a real photo (a face with
both hands near it) before this test was written: face + both hands
detected with plausible boxes, and SAM2 produced a real, non-rectangular
face-shaped mask (not just its bounding box) from that detection's box
prompt — see docs/architecture.md for how detection/segmentation share the
GPU with ComfyUI.
"""

from __future__ import annotations

import io
from uuid import uuid4

import pytest
from PIL import Image, ImageDraw

from app.adapters.http.dependencies import get_image_detector, get_image_segmenter
from app.domain.value_objects.region_type import RegionType

pytestmark = pytest.mark.live_models


def _synthetic_portrait_bytes() -> bytes:
    """A crude but real raster image — enough to prove the pipeline runs
    end-to-end without crashing (weights load, inference executes, output
    is well-formed) even though a hand-drawn oval won't reliably trigger a
    real face detector. Detection *quality* was verified manually against
    an actual photo; see the module docstring."""
    image = Image.new("RGB", (640, 480), color=(220, 220, 220))
    draw = ImageDraw.Draw(image)
    draw.ellipse((220, 80, 420, 300), fill=(200, 170, 150))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_yolo_detector_runs_without_crashing():
    detector = get_image_detector()
    regions = detector.detect(_synthetic_portrait_bytes(), image_id=uuid4())
    assert isinstance(regions, list)  # an empty result is fine; a crash is not
    for region in regions:
        assert region.region_type in {RegionType.FACE, RegionType.LEFT_HAND, RegionType.RIGHT_HAND}


def test_sam2_segmenter_produces_a_full_size_mask_for_a_box_prompt():
    from app.domain.entities.region import DetectedRegion
    from app.domain.value_objects.bounding_box import BoundingBox

    image_bytes = _synthetic_portrait_bytes()
    region = DetectedRegion.new(
        image_id=uuid4(),
        region_type=RegionType.FACE,
        bounding_box=BoundingBox(x_min=220, y_min=80, x_max=420, y_max=300),
        confidence=0.9,
    )

    segmenter = get_image_segmenter()
    result = segmenter.segment(image_bytes, region)

    assert result.width == 640
    assert result.height == 480
    assert len(result.mask_png_bytes) > 0
