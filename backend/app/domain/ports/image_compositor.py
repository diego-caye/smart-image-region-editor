from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.value_objects.bounding_box import BoundingBox


class ImageCompositor(ABC):
    """Merges an edited region back onto a full image so that everything
    outside the (grown + feathered) mask is guaranteed unchanged from the
    original. This port — not the editing model — is what we rely on for
    "no seams / nothing else changes"."""

    @abstractmethod
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
        """mask_png_bytes is full-size (same dimensions as
        original_png_bytes). edited_region_png_bytes covers region_box.
        grow_px dilates the mask before feathering — needed because an edit
        can change a region's silhouette (e.g. a fist opening into a peace
        sign extends past the original hand's outline); without growing the
        mask first, the parts of the new shape that fall outside the old
        one get cut off. Returns full-image PNG bytes where pixels outside
        the grown/feathered mask are byte-identical to original_png_bytes.
        """
        ...
