"""Evaluates the property the whole product depends on: pixels outside an
edited region's mask stay unchanged between the original and final image.
`adapters/imaging/pillow_image_compositor.py` is what's supposed to
*guarantee* this at generation time; this module *measures* it after the
fact, at pixel level, over the golden dataset (see ../datasets/README.md)
or any other original/final/mask triple — including confirmed edits
straight out of the running app, not just synthetic test fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image


@dataclass(slots=True)
class RegionPreservationResult:
    mean_absolute_difference: float  # 0-255 scale, averaged over RGB channels
    max_absolute_difference: int
    changed_pixel_fraction: float  # fraction of outside-mask pixels exceeding pixel_tolerance
    passed: bool


def evaluate_region_preservation(
    original_png_bytes: bytes,
    final_png_bytes: bytes,
    mask_png_bytes: bytes,
    *,
    pixel_tolerance: int = 8,
    max_changed_fraction: float = 0.01,
) -> RegionPreservationResult:
    """pixel_tolerance absorbs harmless PNG/JPEG round-trip noise; a pixel
    only counts as "changed" if any RGB channel differs by more than that.
    passed requires the *fraction* of such pixels (over everything outside
    the mask) to stay at or below max_changed_fraction — a handful of
    stray pixels near a compression artifact shouldn't fail the check, a
    systematic change over the background should.
    """
    original = np.asarray(Image.open(BytesIO(original_png_bytes)).convert("RGB"), dtype=np.int16)
    final = np.asarray(Image.open(BytesIO(final_png_bytes)).convert("RGB"), dtype=np.int16)
    mask = np.asarray(Image.open(BytesIO(mask_png_bytes)).convert("L"))

    if original.shape != final.shape:
        raise ValueError(f"original/final size mismatch: {original.shape} vs {final.shape}")
    if mask.shape != original.shape[:2]:
        raise ValueError(f"mask size mismatch: {mask.shape} vs {original.shape[:2]}")

    outside = mask == 0
    if not outside.any():
        return RegionPreservationResult(0.0, 0, 0.0, True)

    diff = np.abs(original - final)[outside]
    per_pixel_max_channel_diff = diff.max(axis=-1)

    changed_fraction = float((per_pixel_max_channel_diff > pixel_tolerance).mean())

    return RegionPreservationResult(
        mean_absolute_difference=float(diff.mean()),
        max_absolute_difference=int(diff.max()),
        changed_pixel_fraction=changed_fraction,
        passed=changed_fraction <= max_changed_fraction,
    )
