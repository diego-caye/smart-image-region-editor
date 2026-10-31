"""Implements ImageDetector using two YOLOv8 models (face, hand). This is
the translation boundary between raw infra detections (pixel boxes + a
string label) and Domain's DetectedRegion/RegionType — including the
left/right hand disambiguation heuristic, which is a judgment call belonging
here, not a Domain rule.
"""

from __future__ import annotations

from io import BytesIO
from uuid import UUID

from PIL import Image as PILImage

from app.domain.entities.region import DetectedRegion
from app.domain.ports.image_detector import ImageDetector
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.region_type import RegionType
from app.infrastructure.vision.device import release_cuda_memory
from app.infrastructure.vision.yolo_detector import RawDetection, YoloDetector


class YoloImageDetector(ImageDetector):
    def __init__(self, face_detector: YoloDetector, hand_detector: YoloDetector) -> None:
        self._face_detector = face_detector
        self._hand_detector = hand_detector

    def detect(self, image_bytes: bytes, *, image_id: UUID) -> list[DetectedRegion]:
        image_width = PILImage.open(BytesIO(image_bytes)).width

        try:
            face_detections = self._face_detector.detect(image_bytes)
            hand_detections = self._hand_detector.detect(image_bytes)
        finally:
            # Both models ran on whichever device settings.detection_device
            # resolved to; if that's CUDA, free it now so it doesn't compete
            # with ComfyUI's Qwen edit step later in the flow.
            release_cuda_memory()

        regions = [_to_region(image_id, RegionType.FACE, d) for d in face_detections]
        regions += [
            _to_region(image_id, region_type, detection)
            for detection, region_type in _assign_hand_sides(hand_detections, image_width)
        ]
        return regions


def _to_region(image_id: UUID, region_type: RegionType, detection: RawDetection) -> DetectedRegion:
    return DetectedRegion.new(
        image_id=image_id,
        region_type=region_type,
        bounding_box=BoundingBox(
            x_min=detection.x_min,
            y_min=detection.y_min,
            x_max=detection.x_max,
            y_max=detection.y_max,
        ),
        confidence=detection.confidence,
    )


def _assign_hand_sides(
    detections: list[RawDetection], image_width: int
) -> list[tuple[RawDetection, RegionType]]:
    """MVP heuristic, not a precise handedness classifier — hand_yolov8n.pt
    detects "a hand", not which one. With two hands, the one further left on
    screen is taken as the subject's right hand (mirror convention, i.e. as
    seen in a photo/mirror) and vice versa; with one hand, its position
    relative to the image's horizontal midpoint decides. With more than two
    (false positives, or more than one person in frame) only the outermost
    left/right pair is kept — the rest are dropped rather than guessed at.

    Upgrading this later (e.g. a pose model with wrist/elbow keypoints) is a
    self-contained change to this function; nothing above ImageDetector
    needs to know.
    """
    if not detections:
        return []

    if len(detections) == 1:
        detection = detections[0]
        center_x = (detection.x_min + detection.x_max) / 2
        region_type = RegionType.RIGHT_HAND if center_x < image_width / 2 else RegionType.LEFT_HAND
        return [(detection, region_type)]

    sorted_detections = sorted(detections, key=lambda d: (d.x_min + d.x_max) / 2)
    leftmost, rightmost = sorted_detections[0], sorted_detections[-1]
    return [(leftmost, RegionType.RIGHT_HAND), (rightmost, RegionType.LEFT_HAND)]
