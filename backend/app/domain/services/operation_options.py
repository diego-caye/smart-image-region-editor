from __future__ import annotations

from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor

# Garment operations take a color from the fixed palette; nothing else does.
# Domain rule, like which operations go on which region: "a jacket comes in
# a color, a peace sign doesn't" holds regardless of the editing model.
_COLORED_OPERATIONS = frozenset(
    {
        EditOperation.SHIRT_COLOR,
        EditOperation.T_SHIRT,
        EditOperation.JACKET,
        EditOperation.HOODIE,
        EditOperation.PANTS_COLOR,
        EditOperation.SHORTS,
    }
)


class InvalidOperationOptions(ValueError):
    pass


def takes_color(operation: EditOperation) -> bool:
    return operation in _COLORED_OPERATIONS


def ensure_valid_options(operation: EditOperation, color: GarmentColor | None) -> None:
    if takes_color(operation) and color is None:
        raise InvalidOperationOptions(f"Operation '{operation}' needs a color")
    if not takes_color(operation) and color is not None:
        raise InvalidOperationOptions(f"Operation '{operation}' doesn't take a color")
