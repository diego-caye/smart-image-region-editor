"""Runs each golden-dataset entry (see datasets/README.md) through the
REAL pipeline — SAM2 segmenter, ComfyUI/Qwen editor, Pillow compositor —
and checks both region_preservation (nothing outside the mask changed) and
edit_quality (the requested operation actually happened). Opt-in
(`pytest -m live_comfyui`) since it needs the real ComfyUI + GPU, same as
test_comfyui_edit_live.py.

Entries with a `source_url` are downloaded into datasets/images/
(gitignored) on first run, so the bundled entries work on a fresh clone.
Entries without one, whose image isn't present locally, are skipped — that
is how you add your own photos without committing them.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.adapters.http.dependencies import (
    get_image_compositor,
    get_image_editor,
    get_image_segmenter,
)
from app.domain.entities.region import DetectedRegion
from app.domain.services.mask_rules import mask_grow_px_for
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.region_type import RegionType
from tests.evaluation.dataset_images import all_entries, ensure_image, square_crop
from tests.evaluation.evaluators.edit_quality import evaluate_edit_quality
from tests.evaluation.evaluators.region_preservation import evaluate_region_preservation

pytestmark = pytest.mark.live_comfyui


@pytest.mark.parametrize("entry", all_entries(), ids=lambda e: e.get("id", "?"))
def test_golden_entry(entry: dict):
    image_path = ensure_image(entry)
    if image_path is None:
        pytest.skip(f"{entry['image_path']} not present locally — see datasets/README.md")

    image_bytes = image_path.read_bytes()
    region_type = RegionType(entry["region_type"])
    region = DetectedRegion.new(
        image_id=uuid4(),
        region_type=region_type,
        bounding_box=BoundingBox(*entry["region_box"]),
        confidence=1.0,
    )
    operation = EditOperation(entry["operation"])

    segmentation = get_image_segmenter().segment(image_bytes, region)
    editor_result = get_image_editor().edit(
        image_png_bytes=image_bytes,
        mask_png_bytes=segmentation.mask_png_bytes,
        region_box=region.bounding_box,
        operation=operation,
    )
    final_bytes = get_image_compositor().composite(
        original_png_bytes=image_bytes,
        edited_region_png_bytes=editor_result.edited_region_png_bytes,
        region_box=editor_result.region_box_used,
        mask_png_bytes=segmentation.mask_png_bytes,
        grow_px=entry.get("grow_px", mask_grow_px_for(region_type)),
        feather_px=entry.get("feather_px", 12),
    )

    preservation = evaluate_region_preservation(
        image_bytes,
        final_bytes,
        segmentation.mask_png_bytes,
        pixel_tolerance=entry.get("pixel_tolerance", 8),
        max_changed_fraction=entry.get("max_changed_fraction", 0.01),
    )
    quality = evaluate_edit_quality(
        square_crop(image_bytes, region.bounding_box),
        square_crop(final_bytes, region.bounding_box),
        region_type,
        operation,
        min_score=entry.get("min_quality_score", 0.5),
    )

    problems = []
    if not preservation.passed:
        problems.append(
            f"region_preservation: {preservation.changed_pixel_fraction:.2%} of "
            f"outside-mask pixels changed (mean abs diff "
            f"{preservation.mean_absolute_difference:.1f})"
        )
    if not quality.passed:
        problems.append(f"edit_quality: {quality.notes}")
    assert not problems, f"'{entry['id']}' failed — " + "; ".join(problems)
