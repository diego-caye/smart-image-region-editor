from app.domain.services.mask_rules import mask_grow_px_for
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
