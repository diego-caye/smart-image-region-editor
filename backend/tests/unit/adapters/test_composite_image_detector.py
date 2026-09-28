"""CompositeImageDetector wiring: does it feed YOLO's face box into the
MediaPipe stage, and does it concatenate all regions? Exercised with
duck-typed fakes for both sub-detectors — no real YOLO/MediaPipe models."""

from __future__ import annotations

from uuid import uuid4

from app.adapters.vision.composite_image_detector import CompositeImageDetector
from app.domain.entities.region import DetectedRegion
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.region_type import RegionType


def _png_bytes(width=400, height=300) -> bytes:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeYoloDetector:
    def __init__(self, regions: list[DetectedRegion]) -> None:
        self._regions = regions

    def detect(self, image_bytes: bytes, *, image_id):
        return self._regions


class FakeMediaPipeDetector:
    def __init__(
        self, mouth_eyes: list[DetectedRegion] | None = None, body: list[DetectedRegion] | None = None
    ) -> None:
        self._mouth_eyes = mouth_eyes or []
        self._body = body or []
        self.mouth_eyes_calls: list[BoundingBox] = []

    def detect_mouth_and_eyes(self, image_bytes: bytes, face_box: BoundingBox, *, image_id):
        self.mouth_eyes_calls.append(face_box)
        return self._mouth_eyes

    def detect_body(self, image_bytes: bytes, *, image_id):
        return self._body


def _region(region_type: RegionType, box: BoundingBox) -> DetectedRegion:
    return DetectedRegion.new(image_id=uuid4(), region_type=region_type, bounding_box=box, confidence=0.9)


def test_composite_detector_passes_yolo_face_box_into_mediapipe_stage():
    face_box = BoundingBox(x_min=10, y_min=10, x_max=60, y_max=60)
    yolo = FakeYoloDetector([_region(RegionType.FACE, face_box)])
    mediapipe = FakeMediaPipeDetector()
    detector = CompositeImageDetector(yolo, mediapipe)

    detector.detect(_png_bytes(), image_id=uuid4())

    assert mediapipe.mouth_eyes_calls == [face_box]


def test_composite_detector_skips_mediapipe_face_stage_when_no_face_detected():
    yolo = FakeYoloDetector([])
    mediapipe = FakeMediaPipeDetector()
    detector = CompositeImageDetector(yolo, mediapipe)

    detector.detect(_png_bytes(), image_id=uuid4())

    assert mediapipe.mouth_eyes_calls == []


def test_composite_detector_concatenates_all_regions():
    face_box = BoundingBox(x_min=10, y_min=10, x_max=60, y_max=60)
    hand_box = BoundingBox(x_min=200, y_min=10, x_max=260, y_max=70)
    mouth_box = BoundingBox(x_min=20, y_min=40, x_max=40, y_max=55)
    eyes_box = BoundingBox(x_min=15, y_min=15, x_max=55, y_max=30)
    body_box = BoundingBox(x_min=0, y_min=0, x_max=400, y_max=300)

    yolo = FakeYoloDetector(
        [_region(RegionType.FACE, face_box), _region(RegionType.RIGHT_HAND, hand_box)]
    )
    mediapipe = FakeMediaPipeDetector(
        mouth_eyes=[_region(RegionType.MOUTH, mouth_box), _region(RegionType.EYES, eyes_box)],
        body=[_region(RegionType.BODY, body_box)],
    )
    detector = CompositeImageDetector(yolo, mediapipe)

    regions = detector.detect(_png_bytes(), image_id=uuid4())

    assert {r.region_type for r in regions} == {
        RegionType.FACE,
        RegionType.RIGHT_HAND,
        RegionType.MOUTH,
        RegionType.EYES,
        RegionType.BODY,
    }
    assert len(regions) == 5
