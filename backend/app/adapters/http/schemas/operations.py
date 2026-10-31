from __future__ import annotations

from pydantic import BaseModel

from app.application.dto.list_operations import ListOperationsResult
from app.domain.services.operation_options import takes_color
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor
from app.domain.value_objects.region_type import RegionType

# Display metadata (emoji + label) for each operation. This is presentation,
# not a domain rule — which operations exist per region lives in
# domain/services/region_operation_rules.py; this dict only decides how they
# look in the API response the visual gallery renders from.
_OPERATION_DISPLAY: dict[EditOperation, tuple[str, str]] = {
    EditOperation.WAVE: ("👋", "Wave"),
    EditOperation.PEACE_SIGN: ("✌️", "Peace sign"),
    EditOperation.THUMBS_UP: ("👍", "Thumbs up"),
    EditOperation.FIST: ("✊", "Fist"),
    EditOperation.SMILE: ("🙂", "Smile"),
    EditOperation.SMILE_WITH_TEETH: ("😁", "Smile with teeth"),
    EditOperation.CLOSED_MOUTH: ("😐", "Closed mouth"),
    EditOperation.OPEN_EYES: ("👀", "Open eyes"),
    EditOperation.CLOSED_EYES: ("😌", "Closed eyes"),
    EditOperation.SUNGLASSES: ("🕶️", "Sunglasses"),
    EditOperation.GLOVES: ("🧤", "Gloves"),
    EditOperation.SHIRT_COLOR: ("👔", "Shirt color"),
    EditOperation.T_SHIRT: ("👕", "T-shirt"),
    EditOperation.JACKET: ("🧥", "Jacket"),
    EditOperation.HOODIE: ("👚", "Hoodie"),
    EditOperation.BLUE_JEANS: ("👖", "Blue jeans"),
    EditOperation.PANTS_COLOR: ("🎨", "Pants color"),
    EditOperation.SHORTS: ("🩳", "Shorts"),
    EditOperation.WRISTWATCH: ("⌚", "Wristwatch"),
    EditOperation.BRACELET: ("📿", "Bracelet"),
}


def operation_display(operation: EditOperation) -> tuple[str, str]:
    """(emoji, label) for an operation."""
    return _OPERATION_DISPLAY[operation]


class OperationResponse(BaseModel):
    operation: EditOperation
    label: str
    emoji: str
    # The palette to pick from when the operation takes a color; empty when
    # it doesn't (and then the edit request must not send one).
    colors: list[GarmentColor]

    @staticmethod
    def from_operation(operation: EditOperation) -> OperationResponse:
        emoji, label = operation_display(operation)
        return OperationResponse(
            operation=operation,
            label=label,
            emoji=emoji,
            colors=list(GarmentColor) if takes_color(operation) else [],
        )


class ListOperationsResponse(BaseModel):
    region_type: RegionType
    operations: list[OperationResponse]

    @staticmethod
    def from_result(result: ListOperationsResult) -> ListOperationsResponse:
        return ListOperationsResponse(
            region_type=result.region_type,
            operations=[OperationResponse.from_operation(op) for op in result.operations],
        )
