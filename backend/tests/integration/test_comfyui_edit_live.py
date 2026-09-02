"""Opt-in test against the REAL local ComfyUI + Qwen Image Edit (not run by
default — see pyproject.toml's `addopts`). Run explicitly with:

    pytest -m live_comfyui

Requires the local ComfyUI server running at Settings.comfyui_base_url with
the Qwen Image Edit model files in place. Manually verified once end-to-end
against a real photo before this test was written (see
docs/architecture.md): a closed-fist hand correctly became a clean peace
sign, with the rest of the image (face, hair, collar, other hand)
unchanged — including the "grown mask" fix for edits that change a
region's silhouette (see PillowImageCompositor's grow_px).
"""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from app.adapters.http.dependencies import get_image_editor
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.edit_operation import EditOperation

pytestmark = pytest.mark.live_comfyui


def _sample_image_png_bytes() -> bytes:
    image = Image.new("RGB", (300, 300), color=(230, 200, 180))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _full_mask_png_bytes(size: tuple[int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("L", size, color=255).save(buffer, format="PNG")
    return buffer.getvalue()


def test_comfyui_image_editor_returns_a_correctly_sized_edit():
    editor = get_image_editor()
    region_box = BoundingBox(x_min=100, y_min=100, x_max=200, y_max=200)

    result = editor.edit(
        image_png_bytes=_sample_image_png_bytes(),
        mask_png_bytes=_full_mask_png_bytes((300, 300)),
        region_box=region_box,
        operation=EditOperation.PEACE_SIGN,
    )

    edited = Image.open(BytesIO(result.edited_region_png_bytes))
    # region_box_used includes the crop-context margin, so it's larger
    # than region_box but still within the source image.
    assert result.region_box_used.width >= region_box.width
    assert edited.size == (result.region_box_used.width, result.region_box_used.height)
    assert result.seed is not None
    assert "prompt" in result.model_metadata
