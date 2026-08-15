from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.region_type import RegionType


@dataclass(slots=True)
class DetectedRegion:
    """A region an ImageDetector found in an Image. mask_id is set once an
    ImageSegmenter has produced a precise Mask for it (segmentation is lazy —
    it only happens when a region is actually about to be edited).
    """

    id: UUID
    image_id: UUID
    region_type: RegionType
    bounding_box: BoundingBox
    confidence: float
    mask_id: UUID | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    @staticmethod
    def new(
        *, image_id: UUID, region_type: RegionType, bounding_box: BoundingBox, confidence: float
    ) -> DetectedRegion:
        return DetectedRegion(
            id=uuid4(),
            image_id=image_id,
            region_type=region_type,
            bounding_box=bounding_box,
            confidence=confidence,
        )

    def with_mask(self, mask_id: UUID) -> DetectedRegion:
        return DetectedRegion(
            id=self.id,
            image_id=self.image_id,
            region_type=self.region_type,
            bounding_box=self.bounding_box,
            confidence=self.confidence,
            mask_id=mask_id,
        )
