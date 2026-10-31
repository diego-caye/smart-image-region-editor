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

Set GOLDEN_OUTPUT_DIR to also write each entry's final image there
(`<id>.png`), for eyeballing what the scores mean.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from uuid import uuid4

import pytest

from app.adapters.http.dependencies import (
    get_image_compositor,
    get_image_editor,
    get_image_segmenter,
)
from app.adapters.imaging.pillow_image_compositor import blend_mask
from app.domain.entities.region import DetectedRegion
from app.domain.services.mask_rules import mask_grow_px_for
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor
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
    color = GarmentColor(entry["color"]) if "color" in entry else None

    segmentation = get_image_segmenter().segment(image_bytes, region)
    editor_result = get_image_editor().edit(
        image_png_bytes=image_bytes,
        mask_png_bytes=segmentation.mask_png_bytes,
        region_box=region.bounding_box,
        operation=operation,
        color=color,
    )
    grow_px = entry.get("grow_px", mask_grow_px_for(region_type))
    feather_px = entry.get("feather_px", 12)
    final_bytes = get_image_compositor().composite(
        original_png_bytes=image_bytes,
        edited_region_png_bytes=editor_result.edited_region_png_bytes,
        region_box=editor_result.region_box_used,
        mask_png_bytes=segmentation.mask_png_bytes,
        grow_px=grow_px,
        feather_px=feather_px,
    )

    # Measured against the mask the compositor actually blended with, not
    # the raw segmentation: the grown+feathered band changes by design.
    effective_mask = io.BytesIO()
    blend_mask(
        segmentation.mask_png_bytes,
        editor_result.region_box_used,
        grow_px=grow_px,
        feather_px=feather_px,
    ).save(effective_mask, format="PNG")

    preservation = evaluate_region_preservation(
        image_bytes,
        final_bytes,
        effective_mask.getvalue(),
        pixel_tolerance=entry.get("pixel_tolerance", 8),
        max_changed_fraction=entry.get("max_changed_fraction", 0.01),
    )
    quality = evaluate_edit_quality(
        square_crop(image_bytes, region.bounding_box),
        square_crop(final_bytes, region.bounding_box),
        region_type,
        operation,
        color=color,
        min_score=entry.get("min_quality_score", 0.5),
    )

    if output_dir := os.environ.get("GOLDEN_OUTPUT_DIR"):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        (Path(output_dir) / f"{entry['id']}.png").write_bytes(final_bytes)
    print(f"{entry['id']}: edit_quality {quality.notes}")

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
