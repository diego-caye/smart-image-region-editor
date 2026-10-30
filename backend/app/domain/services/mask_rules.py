from __future__ import annotations

from app.domain.value_objects.region_type import RegionType

# How far past the segmented outline an edit to a region may legitimately
# reach. A gesture can change the region's silhouette (a fist opening into a
# spread-finger peace sign extends well past the fist's own outline), so it
# needs a generous margin or the new shape gets clipped. A garment or
# accessory keeps the silhouette, so a tight margin is better there: it
# stops any change the model makes around a torso (sleeves, background)
# from leaking into the composite.
_SILHOUETTE_CHANGING_GROW_PX = 40
_SILHOUETTE_PRESERVING_GROW_PX = 16

_SILHOUETTE_PRESERVING = frozenset(
    {RegionType.TORSO, RegionType.LEFT_ARM, RegionType.RIGHT_ARM, RegionType.LEGS}
)


def mask_grow_px_for(region_type: RegionType) -> int:
    if region_type in _SILHOUETTE_PRESERVING:
        return _SILHOUETTE_PRESERVING_GROW_PX
    return _SILHOUETTE_CHANGING_GROW_PX
