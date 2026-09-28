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


def test_face_and_body_have_no_operations_yet():
    assert operations_allowed_for(RegionType.FACE) == frozenset()
    assert operations_allowed_for(RegionType.BODY) == frozenset()
