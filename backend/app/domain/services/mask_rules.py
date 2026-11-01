from __future__ import annotations

from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.mask_scope import MaskScope
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


# Torso garments that go under whatever is worn over them. The torso's
# whole-region mask includes an open jacket, sleeves and all, so with it a
# real hoodie edit repainted the jacket's sleeves as hoodie sleeves (1 of 4
# runs) — and telling the model to leave the jacket alone made it 7 of 7.
# A jacket edit replaces the outer layer, so it keeps the whole region.
_INNER_LAYER_OPERATIONS = frozenset(
    {EditOperation.SHIRT_COLOR, EditOperation.T_SHIRT, EditOperation.HOODIE}
)


def mask_scope_for(region_type: RegionType, operation: EditOperation) -> MaskScope:
    if region_type is RegionType.TORSO and operation in _INNER_LAYER_OPERATIONS:
        return MaskScope.INNER_LAYER
    return MaskScope.WHOLE_REGION
