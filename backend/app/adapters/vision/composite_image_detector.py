"""Combines YoloImageDetector (face/hands) with MediaPipeRegionDetector
(mouth/eyes/body) behind a single ImageDetector — AnalyzeImageUseCase and
everything above it stays unaware that two different ML stacks are involved.

Mouth/eyes detection needs a face box to crop around (see
mediapipe_region_detector.py's module docstring for why), so this class is
the one place that wires YOLO's face output into MediaPipe's input — that
dependency is an adapter-level judgment call, not a Domain rule.
"""

from __future__ import annotations

from uuid import UUID

from app.adapters.vision.mediapipe_region_detector import MediaPipeRegionDetector
from app.adapters.vision.yolo_sam2_image_detector import YoloImageDetector
from app.domain.entities.region import DetectedRegion
from app.domain.ports.image_detector import ImageDetector
from app.domain.value_objects.region_type import RegionType


class CompositeImageDetector(ImageDetector):
    def __init__(
        self, yolo_detector: YoloImageDetector, mediapipe_detector: MediaPipeRegionDetector
    ) -> None:
        self._yolo_detector = yolo_detector
        self._mediapipe_detector = mediapipe_detector

    def detect(self, image_bytes: bytes, *, image_id: UUID) -> list[DetectedRegion]:
        regions = self._yolo_detector.detect(image_bytes, image_id=image_id)

        face_region = next((r for r in regions if r.region_type == RegionType.FACE), None)
        if face_region is not None:
            regions += self._mediapipe_detector.detect_mouth_and_eyes(
                image_bytes, face_region.bounding_box, image_id=image_id
            )

        regions += self._mediapipe_detector.detect_body(image_bytes, image_id=image_id)

        return regions
