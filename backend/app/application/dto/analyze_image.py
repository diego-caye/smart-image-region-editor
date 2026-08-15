from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from app.domain.value_objects.region_type import RegionType

if TYPE_CHECKING:
    from app.domain.entities.region import DetectedRegion


@dataclass(slots=True)
class RegionSummary:
    region_id: UUID
    region_type: RegionType
    x: int
    y: int
    width: int
    height: int
    confidence: float


@dataclass(slots=True)
class AnalyzeImageResult:
    image_id: UUID
    regions: list[RegionSummary]


def region_to_summary(region: DetectedRegion) -> RegionSummary:
    return RegionSummary(
        region_id=region.id,
        region_type=region.region_type,
        x=region.bounding_box.x_min,
        y=region.bounding_box.y_min,
        width=region.bounding_box.width,
        height=region.bounding_box.height,
        confidence=region.confidence,
    )
