from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.region import DetectedRegion


class ImageDetector(ABC):
    """Finds candidate regions (face, hands, ...) in an image and returns
    their bounding boxes. Detectors are expected to be fast/coarse; precise
    pixel masks are a separate concern (see ImageSegmenter), computed lazily
    only for regions that actually get edited.
    """

    @abstractmethod
    def detect(self, image_bytes: bytes, *, image_id: UUID) -> list[DetectedRegion]: ...
