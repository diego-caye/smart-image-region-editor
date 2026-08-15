from app.application.use_cases.list_operations_for_region import ListOperationsForRegionUseCase
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.region_type import RegionType


def test_lists_hand_gestures_for_right_hand():
    result = ListOperationsForRegionUseCase().execute(RegionType.RIGHT_HAND)
    assert EditOperation.PEACE_SIGN in result.operations
    assert EditOperation.SMILE not in result.operations


def test_lists_no_operations_for_face_in_mvp():
    result = ListOperationsForRegionUseCase().execute(RegionType.FACE)
    assert result.operations == []
