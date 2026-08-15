from __future__ import annotations

from uuid import UUID

from app.application.dto.analyze_image import AnalyzeImageResult, region_to_summary
from app.domain.ports.image_detector import ImageDetector
from app.domain.ports.image_repository import ImageRepository
from app.domain.ports.image_storage import ImageStorage


class ImageNotFound(ValueError):
    pass


class AnalyzeImageUseCase:
    """Runs detection over a previously uploaded image and persists the
    regions found. Safe to call again later (e.g. after adding a new region
    type's detector) — it simply appends newly found regions."""

    def __init__(
        self,
        image_repository: ImageRepository,
        image_storage: ImageStorage,
        image_detector: ImageDetector,
    ) -> None:
        self._repo = image_repository
        self._storage = image_storage
        self._detector = image_detector

    def execute(self, image_id: UUID) -> AnalyzeImageResult:
        image = self._repo.get_image(image_id)
        if image is None:
            raise ImageNotFound(str(image_id))

        image_bytes = self._storage.load(image.storage_ref)
        regions = self._detector.detect(image_bytes, image_id=image.id)
        self._repo.save_regions(regions)

        return AnalyzeImageResult(
            image_id=image.id,
            regions=[region_to_summary(r) for r in regions],
        )
