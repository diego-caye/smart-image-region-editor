"""Unit tests for the region_preservation evaluator itself — synthetic
images, no GPU/ComfyUI needed, runs in the default suite. Complements
tests/unit/adapters/test_pillow_image_compositor.py (which tests the
*compositor's* guarantee); this tests that the *evaluator* correctly tells
apart a preserved case from a violated one.
"""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from tests.evaluation.evaluators.region_preservation import evaluate_region_preservation


def _solid_png(size: tuple[int, int], color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color=color).save(buffer, format="PNG")
    return buffer.getvalue()


def _mask_png(size: tuple[int, int], white_box: tuple[int, int, int, int]) -> bytes:
    mask = Image.new("L", size, color=0)
    mask.paste(255, white_box)
    buffer = BytesIO()
    mask.save(buffer, format="PNG")
    return buffer.getvalue()


def _with_patch(original_png_bytes: bytes, box: tuple[int, int, int, int], color) -> bytes:
    image = Image.open(BytesIO(original_png_bytes)).convert("RGB")
    image.paste(color, box)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_identical_images_pass():
    original = _solid_png((50, 50), (10, 20, 30))
    mask = _mask_png((50, 50), (20, 20, 30, 30))

    result = evaluate_region_preservation(original, original, mask)

    assert result.passed
    assert result.mean_absolute_difference == 0
    assert result.changed_pixel_fraction == 0


def test_a_change_outside_the_mask_fails():
    original = _solid_png((50, 50), (10, 20, 30))
    final = _with_patch(original, (0, 0, 10, 10), (250, 250, 250))  # well outside the mask
    mask = _mask_png((50, 50), (20, 20, 30, 30))

    result = evaluate_region_preservation(original, final, mask)

    assert not result.passed
    assert result.changed_pixel_fraction > 0


def test_a_change_inside_the_mask_is_ignored():
    original = _solid_png((50, 50), (10, 20, 30))
    final = _with_patch(original, (20, 20, 30, 30), (250, 250, 250))  # exactly the masked region
    mask = _mask_png((50, 50), (20, 20, 30, 30))

    result = evaluate_region_preservation(original, final, mask)

    assert result.passed
    assert result.changed_pixel_fraction == 0


def test_small_changes_within_tolerance_still_pass():
    original = _solid_png((50, 50), (100, 100, 100))
    final = _with_patch(original, (0, 0, 10, 10), (103, 103, 103))  # diff of 3, default tolerance is 8
    mask = _mask_png((50, 50), (20, 20, 30, 30))

    result = evaluate_region_preservation(original, final, mask)

    assert result.passed


def test_a_few_stray_pixels_stay_within_max_changed_fraction():
    original = _solid_png((100, 100), (100, 100, 100))
    final = _with_patch(original, (0, 0, 2, 2), (250, 250, 250))  # 4 pixels out of ~9000 outside-mask
    mask = _mask_png((100, 100), (40, 40, 60, 60))

    result = evaluate_region_preservation(original, final, mask, max_changed_fraction=0.01)

    assert result.passed


def test_mismatched_original_final_sizes_raise():
    original = _solid_png((50, 50), (10, 20, 30))
    final = _solid_png((40, 40), (10, 20, 30))
    mask = _mask_png((50, 50), (20, 20, 30, 30))

    with pytest.raises(ValueError, match="size mismatch"):
        evaluate_region_preservation(original, final, mask)


def test_mismatched_mask_size_raises():
    original = _solid_png((50, 50), (10, 20, 30))
    mask = _mask_png((30, 30), (5, 5, 10, 10))

    with pytest.raises(ValueError, match="mask size mismatch"):
        evaluate_region_preservation(original, original, mask)


def test_mask_covering_the_whole_image_trivially_passes():
    original = _solid_png((50, 50), (10, 20, 30))
    final = _with_patch(original, (0, 0, 50, 50), (250, 250, 250))
    mask = _mask_png((50, 50), (0, 0, 50, 50))  # nothing is "outside"

    result = evaluate_region_preservation(original, final, mask)

    assert result.passed
