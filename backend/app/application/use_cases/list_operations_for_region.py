from __future__ import annotations

from app.application.dto.list_operations import ListOperationsResult
from app.domain.services.region_operation_rules import operations_allowed_for
from app.domain.value_objects.region_type import RegionType


class ListOperationsForRegionUseCase:
    """Returns which EditOperations are valid for a RegionType. Pure domain
    rule, no IO — display metadata (labels, emoji) is added later by the
    HTTP adapter, not here."""

    def execute(self, region_type: RegionType) -> ListOperationsResult:
        return ListOperationsResult(
            region_type=region_type,
            operations=sorted(operations_allowed_for(region_type), key=lambda op: op.value),
        )
