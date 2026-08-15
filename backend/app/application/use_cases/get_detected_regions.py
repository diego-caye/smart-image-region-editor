from __future__ import annotations

from uuid import UUID

from app.application.dto.analyze_image import AnalyzeImageResult, region_to_summary
from app.domain.ports.image_repository import ImageRepository


class GetDetectedRegionsUseCase:
    """Reads back the regions already stored for an image, without running
    detection again."""

    def __init__(self, image_repository: ImageRepository) -> None:
        self._repo = image_repository

    def execute(self, image_id: UUID) -> AnalyzeImageResult:
        regions = self._repo.get_regions_for_image(image_id)
        return AnalyzeImageResult(
            image_id=image_id, regions=[region_to_summary(r) for r in regions]
        )
