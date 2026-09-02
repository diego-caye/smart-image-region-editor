"""Runs each golden-dataset entry (see datasets/README.md) through the
REAL pipeline — SAM2 segmenter, ComfyUI/Qwen editor, Pillow compositor —
and checks region_preservation. Opt-in (`pytest -m live_comfyui`) since it
needs the real ComfyUI + GPU, same as test_comfyui_edit_live.py.

Entries whose image_path doesn't exist locally are skipped, not failed —
this repo ships the schema and the runner, not real people's photos (see
datasets/README.md). With the datasets currently empty, this collects as a
single "skipped: got empty parameter set" test — the mechanism is real and
ready, just waiting for entries.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.adapters.http.dependencies import get_image_compositor, get_image_editor, get_image_segmenter
from app.domain.entities.region import DetectedRegion
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.region_type import RegionType
from tests.evaluation.evaluators.region_preservation import evaluate_region_preservation

pytestmark = pytest.mark.live_comfyui

DATASETS_DIR = Path(__file__).parent / "datasets"
_MANIFEST_FILENAMES = ("golden_face_edits.json", "golden_hand_edits.json", "golden_mouth_edits.json")


def _all_entries() -> list[dict]:
    entries = []
    for filename in _MANIFEST_FILENAMES:
        manifest = json.loads((DATASETS_DIR / filename).read_text(encoding="utf-8"))
        entries.extend(manifest["entries"])
    return entries


@pytest.mark.parametrize("entry", _all_entries(), ids=lambda e: e.get("id", "?"))
def test_golden_entry_preserves_the_region_outside_the_mask(entry: dict):
    image_path = DATASETS_DIR / entry["image_path"]
    if not image_path.is_file():
        pytest.skip(f"{entry['image_path']} not present locally — see datasets/README.md")

    image_bytes = image_path.read_bytes()
    region = DetectedRegion.new(
        image_id=uuid4(),
        region_type=RegionType(entry["region_type"]),
        bounding_box=BoundingBox(*entry["region_box"]),
        confidence=1.0,
    )
    operation = EditOperation(entry["operation"])

    segmenter = get_image_segmenter()
    editor = get_image_editor()
    compositor = get_image_compositor()

    segmentation = segmenter.segment(image_bytes, region)
    editor_result = editor.edit(
        image_png_bytes=image_bytes,
        mask_png_bytes=segmentation.mask_png_bytes,
        region_box=region.bounding_box,
        operation=operation,
    )
    final_bytes = compositor.composite(
        original_png_bytes=image_bytes,
        edited_region_png_bytes=editor_result.edited_region_png_bytes,
        region_box=editor_result.region_box_used,
        mask_png_bytes=segmentation.mask_png_bytes,
        grow_px=entry.get("grow_px", 40),
        feather_px=entry.get("feather_px", 12),
    )

    result = evaluate_region_preservation(
        image_bytes,
        final_bytes,
        segmentation.mask_png_bytes,
        pixel_tolerance=entry.get("pixel_tolerance", 8),
        max_changed_fraction=entry.get("max_changed_fraction", 0.01),
    )
    assert result.passed, (
        f"region_preservation failed for '{entry['id']}': "
        f"{result.changed_pixel_fraction:.2%} of outside-mask pixels changed "
        f"beyond tolerance (mean abs diff {result.mean_absolute_difference:.1f})"
    )
