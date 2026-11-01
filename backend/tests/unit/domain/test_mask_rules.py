from app.domain.services.mask_rules import mask_grow_px_for, mask_scope_for
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.mask_scope import MaskScope
from app.domain.value_objects.region_type import RegionType


def test_gesture_regions_get_a_wider_margin_than_garment_regions():
    # A fist opening into a peace sign reaches past its own outline; a
    # recolored shirt doesn't, and a wide margin would let changes around
    # the torso leak into the composite.
    assert mask_grow_px_for(RegionType.RIGHT_HAND) > mask_grow_px_for(RegionType.TORSO)
    assert mask_grow_px_for(RegionType.LEFT_HAND) > mask_grow_px_for(RegionType.LEGS)


def test_every_region_type_has_a_positive_margin():
    for region_type in RegionType:
        assert mask_grow_px_for(region_type) > 0


def test_tops_worn_under_a_jacket_only_get_their_own_layer():
    for operation in (EditOperation.SHIRT_COLOR, EditOperation.T_SHIRT, EditOperation.HOODIE):
        assert mask_scope_for(RegionType.TORSO, operation) is MaskScope.INNER_LAYER


def test_a_jacket_and_everything_else_get_the_whole_region():
    assert mask_scope_for(RegionType.TORSO, EditOperation.JACKET) is MaskScope.WHOLE_REGION
    assert mask_scope_for(RegionType.LEGS, EditOperation.SHORTS) is MaskScope.WHOLE_REGION
    assert mask_scope_for(RegionType.RIGHT_HAND, EditOperation.FIST) is MaskScope.WHOLE_REGION

