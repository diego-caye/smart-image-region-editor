from __future__ import annotations

from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.region_type import RegionType

_HAND_GESTURES = frozenset(
    {EditOperation.WAVE, EditOperation.PEACE_SIGN, EditOperation.THUMBS_UP, EditOperation.FIST}
)
_ARM_ACCESSORIES = frozenset({EditOperation.WRISTWATCH, EditOperation.BRACELET})

# Which EditOperations make sense for which RegionType. This is a domain rule:
# "a peace sign is a thing you do with a hand" is true regardless of which
# framework renders the picker or which model performs the edit — it belongs
# here, not scattered across the HTTP layer or the ComfyUI adapter.
_ALLOWED_OPERATIONS: dict[RegionType, frozenset[EditOperation]] = {
    RegionType.LEFT_HAND: _HAND_GESTURES,
    RegionType.RIGHT_HAND: _HAND_GESTURES,
    RegionType.MOUTH: frozenset(
        {EditOperation.SMILE, EditOperation.SMILE_WITH_TEETH, EditOperation.CLOSED_MOUTH}
    ),
    RegionType.EYES: frozenset({EditOperation.OPEN_EYES, EditOperation.CLOSED_EYES}),
    RegionType.TORSO: frozenset(
        {EditOperation.RED_SHIRT, EditOperation.BLACK_JACKET, EditOperation.WHITE_TSHIRT}
    ),
    RegionType.LEFT_ARM: _ARM_ACCESSORIES,
    RegionType.RIGHT_ARM: _ARM_ACCESSORIES,
    RegionType.LEGS: frozenset({EditOperation.BLUE_JEANS, EditOperation.SHORTS}),
    # Detected and shown, not yet editable — no whole-face/whole-body
    # operation makes sense yet without a much larger, riskier edit than a
    # single gesture, expression, or garment.
    RegionType.FACE: frozenset(),
    RegionType.BODY: frozenset(),
}


def operations_allowed_for(region_type: RegionType) -> frozenset[EditOperation]:
    return _ALLOWED_OPERATIONS.get(region_type, frozenset())


def is_operation_allowed(region_type: RegionType, operation: EditOperation) -> bool:
    return operation in operations_allowed_for(region_type)


class OperationNotAllowedForRegion(ValueError):
    """Raised when a use case tries to apply an operation to a region that
    doesn't support it (e.g. PEACE_SIGN on a FACE region)."""

    def __init__(self, region_type: RegionType, operation: EditOperation) -> None:
        super().__init__(f"Operation '{operation}' is not valid for region '{region_type}'")
        self.region_type = region_type
        self.operation = operation


def ensure_operation_allowed(region_type: RegionType, operation: EditOperation) -> None:
    if not is_operation_allowed(region_type, operation):
        raise OperationNotAllowedForRegion(region_type, operation)
