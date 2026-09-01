"""These tests exercise the adapter's translation logic (raw detections ->
DetectedRegion, left/right hand heuristic) using duck-typed stand-ins for
YoloDetector — no ultralytics/torch import, no GPU, no model weights on
disk. A separate, opt-in live test (test_yolo_sam2_live.py) exercises the
real models."""

from __future__ import annotations

from uuid import uuid4

from app.adapters.vision.yolo_sam2_image_detector import YoloImageDetector
from app.domain.value_objects.region_type import RegionType
from app.infrastructure.vision.yolo_detector import RawDetection


class StubYoloDetector:
    def __init__(self, detections: list[RawDetection]) -> None:
        self._detections = detections

    def detect(self, image_bytes: bytes) -> list[RawDetection]:
        return self._detections


def _png_bytes(width=400, height=300) -> bytes:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_face_detections_become_face_regions():
    face_detector = StubYoloDetector(
        [RawDetection(label="face", x_min=10, y_min=10, x_max=110, y_max=110, confidence=0.9)]
    )
    hand_detector = StubYoloDetector([])
    detector = YoloImageDetector(face_detector, hand_detector)

    regions = detector.detect(_png_bytes(), image_id=uuid4())

    assert len(regions) == 1
    assert regions[0].region_type == RegionType.FACE
    assert regions[0].bounding_box.as_xyxy() == (10, 10, 110, 110)
    assert regions[0].confidence == 0.9


def test_two_hands_assigned_by_left_right_screen_position():
    # image is 400px wide; leftmost box -> subject's RIGHT hand (mirror
    # convention), rightmost box -> subject's LEFT hand
    hand_detector = StubYoloDetector(
        [
            RawDetection(label="hand", x_min=20, y_min=20, x_max=80, y_max=80, confidence=0.8),
            RawDetection(label="hand", x_min=300, y_min=20, x_max=360, y_max=80, confidence=0.7),
        ]
    )
    detector = YoloImageDetector(StubYoloDetector([]), hand_detector)

    regions = detector.detect(_png_bytes(width=400), image_id=uuid4())

    by_type = {r.region_type: r for r in regions}
    assert by_type[RegionType.RIGHT_HAND].bounding_box.x_min == 20
    assert by_type[RegionType.LEFT_HAND].bounding_box.x_min == 300


def test_single_hand_assigned_by_image_midpoint():
    hand_detector = StubYoloDetector(
        [RawDetection(label="hand", x_min=10, y_min=10, x_max=50, y_max=50, confidence=0.9)]
    )
    detector = YoloImageDetector(StubYoloDetector([]), hand_detector)

    # box center (30) is left of the 400px-wide image's midpoint (200) ->
    # mirror convention -> subject's right hand
    regions = detector.detect(_png_bytes(width=400), image_id=uuid4())
    assert regions[0].region_type == RegionType.RIGHT_HAND


def test_more_than_two_hand_detections_keeps_only_the_outer_pair():
    hand_detector = StubYoloDetector(
        [
            RawDetection(label="hand", x_min=20, y_min=0, x_max=60, y_max=40, confidence=0.6),
            RawDetection(label="hand", x_min=150, y_min=0, x_max=190, y_max=40, confidence=0.5),
            RawDetection(label="hand", x_min=300, y_min=0, x_max=340, y_max=40, confidence=0.7),
        ]
    )
    detector = YoloImageDetector(StubYoloDetector([]), hand_detector)

    regions = detector.detect(_png_bytes(width=400), image_id=uuid4())

    assert len(regions) == 2
    assert {r.region_type for r in regions} == {RegionType.RIGHT_HAND, RegionType.LEFT_HAND}


def test_no_hand_detections_yields_no_hand_regions():
    detector = YoloImageDetector(StubYoloDetector([]), StubYoloDetector([]))
    regions = detector.detect(_png_bytes(), image_id=uuid4())
    assert regions == []
