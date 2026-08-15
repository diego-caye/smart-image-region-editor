from __future__ import annotations

from pydantic import BaseModel

from app.application.dto.list_operations import ListOperationsResult
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.region_type import RegionType

# Display metadata (emoji + label) for each operation. This is presentation,
# not a domain rule — which operations exist per region lives in
# domain/services/region_operation_rules.py; this dict only decides how they
# look in the API response the visual gallery renders from.
_OPERATION_DISPLAY: dict[EditOperation, tuple[str, str]] = {
    EditOperation.WAVE: ("👋", "Saludar"),
    EditOperation.PEACE_SIGN: ("✌️", "Señal de paz"),
    EditOperation.THUMBS_UP: ("👍", "Pulgar arriba"),
    EditOperation.FIST: ("✊", "Puño"),
    EditOperation.SMILE: ("🙂", "Sonrisa"),
    EditOperation.SMILE_WITH_TEETH: ("😁", "Sonrisa con dientes"),
    EditOperation.CLOSED_MOUTH: ("😐", "Boca cerrada"),
}


class OperationResponse(BaseModel):
    operation: EditOperation
    label: str
    emoji: str

    @staticmethod
    def from_operation(operation: EditOperation) -> OperationResponse:
        emoji, label = _OPERATION_DISPLAY[operation]
        return OperationResponse(operation=operation, label=label, emoji=emoji)


class ListOperationsResponse(BaseModel):
    region_type: RegionType
    operations: list[OperationResponse]

    @staticmethod
    def from_result(result: ListOperationsResult) -> ListOperationsResponse:
        return ListOperationsResponse(
            region_type=result.region_type,
            operations=[OperationResponse.from_operation(op) for op in result.operations],
        )
