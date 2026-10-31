"""Implements ImageCompositor with Pillow. This is what actually
guarantees "everything outside the mask stays identical" — not a hope
about what the editing model did. Pixels strictly outside the (feathered)
mask are copied byte-for-byte from the original; only a thin band right at
the mask's edge is blended, to avoid a visible seam.
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image as PILImage
from PIL import ImageFilter

from app.domain.ports.image_compositor import ImageCompositor
from app.domain.value_objects.bounding_box import BoundingBox


def blend_mask(
    mask_png_bytes: bytes, region_box: BoundingBox, *, grow_px: int, feather_px: int
) -> PILImage.Image:
    """The full-image "L" mask composite() actually blends with: the
    segmentation mask, grown and feathered within region_box, zero
    everywhere else. Public so the golden dataset's region_preservation
    check measures against exactly this — the raw mask would flag the
    grown/feathered band, which changes by design."""
    full_mask = PILImage.open(BytesIO(mask_png_bytes)).convert("L")
    x0, y0, x1, y1 = region_box.as_xyxy()
    region_mask = full_mask.crop((x0, y0, x1, y1))

    if grow_px > 0:
        # MaxFilter dilates by (kernel_size - 1) / 2 pixels per pass — a
        # square structuring element, not a perfect circle, but correctness
        # here matters far more than a rounded edge (which feathering
        # softens anyway).
        region_mask = region_mask.filter(ImageFilter.MaxFilter(size=2 * grow_px + 1))

    if feather_px > 0:
        region_mask = region_mask.filter(ImageFilter.GaussianBlur(radius=feather_px))

    result = PILImage.new("L", full_mask.size, 0)
    result.paste(region_mask, (x0, y0))
    return result


class PillowImageCompositor(ImageCompositor):
    def composite(
        self,
        *,
        original_png_bytes: bytes,
        edited_region_png_bytes: bytes,
        region_box: BoundingBox,
        mask_png_bytes: bytes,
        grow_px: int,
        feather_px: int,
    ) -> bytes:
        original = PILImage.open(BytesIO(original_png_bytes)).convert("RGB")
        edited_region = PILImage.open(BytesIO(edited_region_png_bytes)).convert("RGB")
        mask = blend_mask(mask_png_bytes, region_box, grow_px=grow_px, feather_px=feather_px)

        if mask.size != original.size:
            raise ValueError(
                f"mask size {mask.size} does not match original image size {original.size}"
            )

        x0, y0, x1, y1 = region_box.as_xyxy()
        region_mask = mask.crop((x0, y0, x1, y1))
        if region_mask.size != edited_region.size:
            edited_region = edited_region.resize(region_mask.size, PILImage.LANCZOS)

        result = original.copy()
        # Image.paste with an "L"-mode mask alpha-blends per pixel using the
        # mask's 0-255 values — this is what turns the feathered edge into a
        # smooth blend while pixels under mask=0 stay byte-identical to
        # `original`.
        result.paste(edited_region, (x0, y0), mask=region_mask)

        buffer = BytesIO()
        result.save(buffer, format="PNG")
        return buffer.getvalue()
