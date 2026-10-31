"""Verifies the property the whole product depends on: pixels outside the
mask are byte-identical to the original after compositing. This is the
same kind of check the golden-dataset region_preservation evaluator will
run later at a larger scale — this is the unit-level guarantee."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from app.adapters.imaging.pillow_image_compositor import PillowImageCompositor, blend_mask
from app.domain.value_objects.bounding_box import BoundingBox


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


def _load_rgb(png_bytes: bytes) -> np.ndarray:
    return np.array(Image.open(BytesIO(png_bytes)).convert("RGB"))


def test_pixels_outside_the_mask_are_byte_identical_to_the_original():
    original = _solid_png((100, 100), (255, 0, 0))
    edited_region = _solid_png((20, 20), (0, 0, 255))
    mask = _mask_png((100, 100), (40, 40, 60, 60))
    region_box = BoundingBox(x_min=40, y_min=40, x_max=60, y_max=60)

    result = PillowImageCompositor().composite(
        original_png_bytes=original,
        edited_region_png_bytes=edited_region,
        region_box=region_box,
        mask_png_bytes=mask,
        grow_px=0,
        feather_px=0,
    )

    original_arr = _load_rgb(original)
    result_arr = _load_rgb(result)

    outside = np.ones((100, 100), dtype=bool)
    outside[40:60, 40:60] = False
    assert np.array_equal(result_arr[outside], original_arr[outside])


def test_with_grow_and_feather_only_pixels_where_blend_mask_is_zero_are_guaranteed():
    # The real contract once the mask is grown and feathered: the band
    # around the raw mask changes by design, everything at blend_mask == 0
    # stays byte-identical. The golden dataset measures against this.
    original = _solid_png((200, 200), (255, 0, 0))
    edited_region = _solid_png((120, 120), (0, 0, 255))
    mask = _mask_png((200, 200), (90, 90, 110, 110))
    region_box = BoundingBox(x_min=40, y_min=40, x_max=160, y_max=160)

    result = PillowImageCompositor().composite(
        original_png_bytes=original,
        edited_region_png_bytes=edited_region,
        region_box=region_box,
        mask_png_bytes=mask,
        grow_px=16,
        feather_px=6,
    )
    effective = np.array(blend_mask(mask, region_box, grow_px=16, feather_px=6))

    original_arr = _load_rgb(original)
    result_arr = _load_rgb(result)
    untouched = effective == 0
    assert np.array_equal(result_arr[untouched], original_arr[untouched])

    raw_outside = np.array(Image.open(BytesIO(mask)).convert("L")) == 0
    changed = np.any(result_arr != original_arr, axis=-1)
    # some pixels outside the raw mask did change — the grown band
    assert (changed & raw_outside).any()


def test_pixels_inside_the_mask_come_from_the_edited_region():
    original = _solid_png((100, 100), (255, 0, 0))
    edited_region = _solid_png((20, 20), (0, 0, 255))
    mask = _mask_png((100, 100), (40, 40, 60, 60))
    region_box = BoundingBox(x_min=40, y_min=40, x_max=60, y_max=60)

    result = PillowImageCompositor().composite(
        original_png_bytes=original,
        edited_region_png_bytes=edited_region,
        region_box=region_box,
        mask_png_bytes=mask,
        grow_px=0,
        feather_px=0,
    )

    result_arr = _load_rgb(result)
    center_pixel = result_arr[50, 50]
    assert tuple(center_pixel) == (0, 0, 255)


def test_feathering_only_affects_a_thin_band_near_the_mask_edge():
    original = _solid_png((100, 100), (255, 0, 0))
    edited_region = _solid_png((20, 20), (0, 0, 255))
    mask = _mask_png((100, 100), (40, 40, 60, 60))
    region_box = BoundingBox(x_min=40, y_min=40, x_max=60, y_max=60)

    result = PillowImageCompositor().composite(
        original_png_bytes=original,
        edited_region_png_bytes=edited_region,
        region_box=region_box,
        mask_png_bytes=mask,
        grow_px=0,
        feather_px=4,
    )

    original_arr = _load_rgb(original)
    result_arr = _load_rgb(result)

    # far away from the mask boundary (more than ~3*feather_px), pixels are
    # still exactly the original
    assert tuple(result_arr[0, 0]) == tuple(original_arr[0, 0])
    assert tuple(result_arr[99, 99]) == tuple(original_arr[99, 99])
    # deep inside the region, still exactly the edited color
    assert tuple(result_arr[50, 50]) == (0, 0, 255)


def test_mismatched_mask_size_raises():
    original = _solid_png((100, 100), (255, 0, 0))
    edited_region = _solid_png((20, 20), (0, 0, 255))
    wrong_size_mask = _mask_png((50, 50), (10, 10, 20, 20))
    region_box = BoundingBox(x_min=40, y_min=40, x_max=60, y_max=60)

    with pytest.raises(ValueError, match="mask size"):
        PillowImageCompositor().composite(
            original_png_bytes=original,
            edited_region_png_bytes=edited_region,
            region_box=region_box,
            mask_png_bytes=wrong_size_mask,
            grow_px=0,
            feather_px=0,
        )


def test_edited_region_is_resized_if_it_does_not_match_the_mask_crop():
    original = _solid_png((100, 100), (255, 0, 0))
    # 10x10 edited region for a 20x20 mask box -> compositor must resize
    edited_region = _solid_png((10, 10), (0, 255, 0))
    mask = _mask_png((100, 100), (40, 40, 60, 60))
    region_box = BoundingBox(x_min=40, y_min=40, x_max=60, y_max=60)

    result = PillowImageCompositor().composite(
        original_png_bytes=original,
        edited_region_png_bytes=edited_region,
        region_box=region_box,
        mask_png_bytes=mask,
        grow_px=0,
        feather_px=0,
    )

    result_arr = _load_rgb(result)
    assert tuple(result_arr[50, 50]) == (0, 255, 0)


def test_without_growing_the_mask_an_edit_that_changed_shape_gets_clipped():
    """Reproduces the real "ghost fingers" bug found end-to-end: the mask
    only covers the region's *original* silhouette (e.g. a closed fist).
    An edit that opens the fist into a spread-finger peace sign extends
    past that silhouette — without growing the mask, those new pixels
    (inside region_box, inside the edited image, but outside the tight
    mask) are dropped and the original shows through instead."""
    original = _solid_png((100, 100), (255, 0, 0))
    edited_region = _solid_png((20, 20), (0, 0, 255))  # covers the full region_box
    tight_mask = _mask_png((100, 100), (45, 45, 55, 55))  # only the old, smaller silhouette
    region_box = BoundingBox(x_min=40, y_min=40, x_max=60, y_max=60)

    result = PillowImageCompositor().composite(
        original_png_bytes=original,
        edited_region_png_bytes=edited_region,
        region_box=region_box,
        mask_png_bytes=tight_mask,
        grow_px=0,
        feather_px=0,
    )

    result_arr = _load_rgb(result)
    # (42, 42) is inside region_box/edited_region but outside the tight
    # mask -> without growing, it wrongly stays the original color.
    assert tuple(result_arr[42, 42]) == (255, 0, 0)


def test_growing_the_mask_recovers_the_full_edited_shape():
    original = _solid_png((100, 100), (255, 0, 0))
    edited_region = _solid_png((20, 20), (0, 0, 255))
    tight_mask = _mask_png((100, 100), (45, 45, 55, 55))
    region_box = BoundingBox(x_min=40, y_min=40, x_max=60, y_max=60)

    result = PillowImageCompositor().composite(
        original_png_bytes=original,
        edited_region_png_bytes=edited_region,
        region_box=region_box,
        mask_png_bytes=tight_mask,
        grow_px=10,
        feather_px=0,
    )

    result_arr = _load_rgb(result)
    # growing the 45-55 mask by 10px reaches (42,42) -> now shows the edit
    assert tuple(result_arr[42, 42]) == (0, 0, 255)
