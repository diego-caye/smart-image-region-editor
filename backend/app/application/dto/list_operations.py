from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.region_type import RegionType


@dataclass(slots=True)
class ListOperationsResult:
    region_type: RegionType
    operations: list[EditOperation]
