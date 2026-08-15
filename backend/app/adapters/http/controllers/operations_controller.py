from __future__ import annotations

from fastapi import APIRouter, Depends

from app.adapters.http.dependencies import get_list_operations_use_case
from app.adapters.http.schemas.operations import ListOperationsResponse
from app.application.use_cases.list_operations_for_region import ListOperationsForRegionUseCase
from app.domain.value_objects.region_type import RegionType

router = APIRouter(prefix="/regions", tags=["operations"])


@router.get("/{region_type}/operations", response_model=ListOperationsResponse)
def list_operations(
    region_type: RegionType,
    use_case: ListOperationsForRegionUseCase = Depends(get_list_operations_use_case),
) -> ListOperationsResponse:
    result = use_case.execute(region_type)
    return ListOperationsResponse.from_result(result)
