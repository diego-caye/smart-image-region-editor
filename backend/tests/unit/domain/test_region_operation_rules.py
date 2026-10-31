import pytest

from app.domain.services.region_operation_rules import (
    OperationNotAllowedForRegion,
    ensure_operation_allowed,
    is_operation_allowed,
    operations_allowed_for,
)
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.region_type import RegionType


def test_peace_sign_allowed_on_hands_not_face():
    assert is_operation_allowed(RegionType.RIGHT_HAND, EditOperation.PEACE_SIGN)
    assert is_operation_allowed(RegionType.LEFT_HAND, EditOperation.PEACE_SIGN)
    assert not is_operation_allowed(RegionType.FACE, EditOperation.PEACE_SIGN)


def test_smile_allowed_on_mouth_not_hand():
    assert is_operation_allowed(RegionType.MOUTH, EditOperation.SMILE_WITH_TEETH)
    assert not is_operation_allowed(RegionType.RIGHT_HAND, EditOperation.SMILE_WITH_TEETH)


def test_ensure_operation_allowed_raises_for_invalid_pair():
    with pytest.raises(OperationNotAllowedForRegion):
        ensure_operation_allowed(RegionType.FACE, EditOperation.FIST)


def test_ensure_operation_allowed_passes_silently_for_valid_pair():
    ensure_operation_allowed(RegionType.LEFT_HAND, EditOperation.FIST)  # no raise


def test_eyes_open_closed_allowed_on_eyes_not_hand():
    assert is_operation_allowed(RegionType.EYES, EditOperation.OPEN_EYES)
    assert is_operation_allowed(RegionType.EYES, EditOperation.CLOSED_EYES)
    assert not is_operation_allowed(RegionType.RIGHT_HAND, EditOperation.CLOSED_EYES)


def test_face_and_whole_body_have_no_operations_yet():
    assert operations_allowed_for(RegionType.FACE) == frozenset()
    assert operations_allowed_for(RegionType.BODY) == frozenset()


def test_garments_go_on_the_region_they_cover():
    assert is_operation_allowed(RegionType.TORSO, EditOperation.SHIRT_COLOR)
    assert is_operation_allowed(RegionType.LEGS, EditOperation.BLUE_JEANS)
    assert not is_operation_allowed(RegionType.LEGS, EditOperation.SHIRT_COLOR)
    assert not is_operation_allowed(RegionType.TORSO, EditOperation.BLUE_JEANS)


def test_accessories_allowed_on_either_arm_but_not_torso():
    assert is_operation_allowed(RegionType.LEFT_ARM, EditOperation.WRISTWATCH)
    assert is_operation_allowed(RegionType.RIGHT_ARM, EditOperation.BRACELET)
    assert not is_operation_allowed(RegionType.TORSO, EditOperation.WRISTWATCH)


def test_every_operation_is_reachable_from_some_region():
    reachable = set().union(*(operations_allowed_for(r) for r in RegionType))
    assert reachable == set(EditOperation)


def test_new_cheap_operations_go_where_they_are_worn():
    assert is_operation_allowed(RegionType.EYES, EditOperation.SUNGLASSES)
    assert is_operation_allowed(RegionType.TORSO, EditOperation.HOODIE)
    assert is_operation_allowed(RegionType.LEFT_HAND, EditOperation.GLOVES)
    assert not is_operation_allowed(RegionType.MOUTH, EditOperation.SUNGLASSES)
