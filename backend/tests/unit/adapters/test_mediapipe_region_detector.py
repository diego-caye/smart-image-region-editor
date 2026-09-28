"""bbox_from_points is pure math (no MediaPipe import needed). The detector
methods are exercised with a duck-typed fake landmarker returning real
Landmarks instances (a plain data container, not a MediaPipe object) — no
model weights on disk, no GPU. A separate, opt-in live test exercises the
real models against person.jpg."""

from __future__ import annotations

from uuid import uuid4

from app.adapters.vision.mediapipe_region_detector import (
    MediaPipeRegionDetector,
    bbox_from_points,
)
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.region_type import RegionType
from app.infrastructure.vision.mediapipe_landmarker import Landmarks


def _png_bytes(width=400, height=300) -> bytes:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeLandmarker:
    def __init__(
        self, face_landmarks: Landmarks | None = None, pose_landmarks: Landmarks | None = None
    ) -> None:
        self._face_landmarks = face_landmarks
        self._pose_landmarks = pose_landmarks
        self.face_calls: list = []
        self.pose_calls: list = []

    def detect_face_landmarks(self, image_rgb):
        self.face_calls.append(image_rgb)
        return self._face_landmarks

    def detect_pose_landmarks(self, image_rgb):
        self.pose_calls.append(image_rgb)
        return self._pose_landmarks


def test_bbox_from_points_covers_only_given_indices():
    # index 2 is excluded from the requested set -> must not influence the
    # box, even though it's the widest point in the list
    points = [(0.1, 0.1), (0.3, 0.3), (0.9, 0.9)]
    box = bbox_from_points(points, {0, 1}, width=100, height=100, padding_ratio=0.0)
    assert box == BoundingBox(x_min=10, y_min=10, x_max=30, y_max=30)


def test_bbox_from_points_pads_and_clamps_to_image_bounds():
    points = [(0.0, 0.0), (0.2, 0.2)]
    box = bbox_from_points(points, {0, 1}, width=100, height=100, padding_ratio=1.0)
    # raw box is (0,0)-(20,20); padding_ratio=1.0 adds 20px on each side,
    # clamped to >= 0
    assert box == BoundingBox(x_min=0, y_min=0, x_max=40, y_max=40)


def test_bbox_from_points_returns_none_when_no_indices_present():
    points = [(0.5, 0.5)]
    box = bbox_from_points(points, {5}, width=100, height=100, padding_ratio=0.1)
    assert box is None


def test_detect_mouth_and_eyes_offsets_boxes_back_to_full_image_coords():
    # 21 landmark points so lip/eye indices (drawn from real MediaPipe
    # connection index sets, some >= 300) resolve; only the ones actually
    # referenced by _lip_indices/_eye_indices need be non-trivial, the rest
    # can be a constant filler.
    from app.adapters.vision.mediapipe_region_detector import _eye_indices, _lip_indices

    lip_idx = sorted(_lip_indices())
    eye_idx = sorted(_eye_indices())
    max_idx = max(lip_idx + eye_idx)
    points = [(0.5, 0.5)] * (max_idx + 1)
    # Spread each group's points slightly (real landmark sets are never a
    # single repeated point) so the resulting box has non-zero width/height.
    for offset, i in enumerate(lip_idx):
        points[i] = (0.4 + 0.001 * offset, 0.6 + 0.001 * offset)
    for offset, i in enumerate(eye_idx):
        points[i] = (0.3 + 0.001 * offset, 0.2 + 0.001 * offset)

    landmarks = Landmarks(points=points, image_width=200, image_height=200)
    landmarker = FakeLandmarker(face_landmarks=landmarks)
    detector = MediaPipeRegionDetector(landmarker, face_crop_margin_px=10)

    face_box = BoundingBox(x_min=50, y_min=50, x_max=150, y_max=150)
    regions = detector.detect_mouth_and_eyes(_png_bytes(400, 400), face_box, image_id=uuid4())

    by_type = {r.region_type: r for r in regions}
    assert RegionType.MOUTH in by_type
    assert RegionType.EYES in by_type
    # crop starts at (40, 40) (face_box expanded by margin 10); mouth point
    # (0.4, 0.6) within a 200x200 crop -> (80, 120) crop-local -> (120, 160)
    # full-image, before padding
    mouth_box = by_type[RegionType.MOUTH].bounding_box
    assert mouth_box.x_min <= 120 <= mouth_box.x_max
    assert mouth_box.y_min <= 160 <= mouth_box.y_max


def test_detect_mouth_and_eyes_returns_empty_when_no_face_landmarks_found():
    landmarker = FakeLandmarker(face_landmarks=None)
    detector = MediaPipeRegionDetector(landmarker, face_crop_margin_px=10)

    face_box = BoundingBox(x_min=10, y_min=10, x_max=60, y_max=60)
    regions = detector.detect_mouth_and_eyes(_png_bytes(), face_box, image_id=uuid4())

    assert regions == []


def test_detect_body_returns_single_region_from_pose_landmarks():
    from app.adapters.vision.mediapipe_region_detector import _body_landmark_indices

    body_idx = sorted(_body_landmark_indices())
    points = [(0.5, 0.5)] * (max(body_idx) + 1)
    for offset, i in enumerate(body_idx):
        points[i] = (0.3 + 0.001 * offset, 0.7 + 0.001 * offset)

    landmarks = Landmarks(points=points, image_width=400, image_height=400)
    landmarker = FakeLandmarker(pose_landmarks=landmarks)
    detector = MediaPipeRegionDetector(landmarker, face_crop_margin_px=10)

    regions = detector.detect_body(_png_bytes(400, 400), image_id=uuid4())

    assert len(regions) == 1
    assert regions[0].region_type == RegionType.BODY


def test_detect_body_returns_empty_when_no_pose_found():
    landmarker = FakeLandmarker(pose_landmarks=None)
    detector = MediaPipeRegionDetector(landmarker, face_crop_margin_px=10)

    regions = detector.detect_body(_png_bytes(), image_id=uuid4())

    assert regions == []
