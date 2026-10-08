"""Implements the MOUTH/EYES/BODY/TORSO/LEFT_ARM/RIGHT_ARM/LEFT_LEG/RIGHT_LEG
portion of detection using MediaPipe's FaceLandmarker (cropped around an
already-detected face box — see docs/architecture.md for why) and
PoseLandmarker (run on the whole image). Landmark index groups
(FACE_LANDMARKS_LIPS, FACE_LANDMARKS_LEFT_EYE/RIGHT_EYE, PoseLandmark) are
imported directly from the installed `mediapipe` package, not hand-copied,
so they stay correct if the package ever changes them.

Not a standalone ImageDetector — mouth/eyes need a face box handed in, so
this is designed to be composed with a face/hand detector via
CompositeImageDetector, not used alone.
"""

from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
from uuid import UUID

import numpy as np
from PIL import Image as PILImage

from app.domain.entities.region import DetectedRegion
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.region_type import RegionType
from app.infrastructure.vision.mediapipe_landmarker import MediaPipeLandmarker

# MediaPipe's Tasks API doesn't expose a single aggregate "how confident is
# this landmark set" score the way YOLO does — a face/pose is either found
# (landmarks present) or not. This is a placeholder, not a calibrated
# probability.
_LANDMARK_REGION_CONFIDENCE = 0.9

_MOUTH_PADDING_RATIO = 0.35
_EYES_PADDING_RATIO = 0.6
_BODY_PADDING_RATIO = 0.05
# Limbs are thin relative to their landmark bounding box's diagonal (the
# landmarks are centerline points, e.g. shoulder/elbow/wrist), so arms/legs
# need more padding than the whole-body envelope to actually cover the
# limb's visible width/sleeve/pant leg.
_TORSO_PADDING_RATIO = 0.15
_ARM_PADDING_RATIO = 0.3
_LEG_PADDING_RATIO = 0.25


def _lip_indices() -> set[int]:
    from mediapipe.tasks.python.vision.face_landmarker import FaceLandmarksConnections

    return {
        i
        for connection in FaceLandmarksConnections.FACE_LANDMARKS_LIPS
        for i in (connection.start, connection.end)
    }


def _eye_indices() -> set[int]:
    from mediapipe.tasks.python.vision.face_landmarker import FaceLandmarksConnections

    connections = (
        FaceLandmarksConnections.FACE_LANDMARKS_LEFT_EYE
        + FaceLandmarksConnections.FACE_LANDMARKS_RIGHT_EYE
    )
    return {i for connection in connections for i in (connection.start, connection.end)}


def _body_landmark_indices() -> set[int]:
    from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmark

    # Shoulders through feet (11-32) — excludes the purely facial pose
    # landmarks (nose/eyes/ears/mouth, 0-10), which the face/mouth/eyes
    # detectors already cover.
    return {landmark.value for landmark in PoseLandmark if landmark.value >= PoseLandmark.LEFT_SHOULDER}


def _torso_indices() -> set[int]:
    from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmark

    return {
        PoseLandmark.LEFT_SHOULDER.value,
        PoseLandmark.RIGHT_SHOULDER.value,
        PoseLandmark.LEFT_HIP.value,
        PoseLandmark.RIGHT_HIP.value,
    }


def _left_arm_indices() -> set[int]:
    from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmark

    return {
        PoseLandmark.LEFT_SHOULDER.value,
        PoseLandmark.LEFT_ELBOW.value,
        PoseLandmark.LEFT_WRIST.value,
        PoseLandmark.LEFT_PINKY.value,
        PoseLandmark.LEFT_INDEX.value,
        PoseLandmark.LEFT_THUMB.value,
    }


def _right_arm_indices() -> set[int]:
    from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmark

    return {
        PoseLandmark.RIGHT_SHOULDER.value,
        PoseLandmark.RIGHT_ELBOW.value,
        PoseLandmark.RIGHT_WRIST.value,
        PoseLandmark.RIGHT_PINKY.value,
        PoseLandmark.RIGHT_INDEX.value,
        PoseLandmark.RIGHT_THUMB.value,
    }


def _left_leg_indices() -> set[int]:
    from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmark

    return {
        PoseLandmark.LEFT_HIP.value,
        PoseLandmark.LEFT_KNEE.value,
        PoseLandmark.LEFT_ANKLE.value,
        PoseLandmark.LEFT_HEEL.value,
        PoseLandmark.LEFT_FOOT_INDEX.value,
    }


def _right_leg_indices() -> set[int]:
    from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmark

    return {
        PoseLandmark.RIGHT_HIP.value,
        PoseLandmark.RIGHT_KNEE.value,
        PoseLandmark.RIGHT_ANKLE.value,
        PoseLandmark.RIGHT_HEEL.value,
        PoseLandmark.RIGHT_FOOT_INDEX.value,
    }


# (region_type, index-set factory, padding ratio) for every region derived
# from a single PoseLandmarker call. LEFT_*/RIGHT_* here is PoseLandmarker's
# own anatomical convention — verified against a real photo's already-known
# YOLO hand boxes to already match this project's RegionType.LEFT_HAND/
# RIGHT_HAND convention (a subject facing the camera has their anatomical
# right hand on screen-left), so no flipping is needed.
_BODY_PART_SPECS: tuple[tuple[RegionType, Callable[[], set[int]], float], ...] = (
    (RegionType.BODY, _body_landmark_indices, _BODY_PADDING_RATIO),
    (RegionType.TORSO, _torso_indices, _TORSO_PADDING_RATIO),
    (RegionType.LEFT_ARM, _left_arm_indices, _ARM_PADDING_RATIO),
    (RegionType.RIGHT_ARM, _right_arm_indices, _ARM_PADDING_RATIO),
    (RegionType.LEFT_LEG, _left_leg_indices, _LEG_PADDING_RATIO),
    (RegionType.RIGHT_LEG, _right_leg_indices, _LEG_PADDING_RATIO),
)


def bbox_from_points(
    points: list[tuple[float, float]],
    indices: set[int],
    *,
    width: int,
    height: int,
    padding_ratio: float,
) -> BoundingBox | None:
    """Pure math: normalized (0-1) landmark points -> a padded pixel
    BoundingBox covering just the given indices. Returns None if none of
    the indices are present (e.g. a landmark set shorter than expected)."""
    xs = [points[i][0] * width for i in indices if i < len(points)]
    ys = [points[i][1] * height for i in indices if i < len(points)]
    if not xs or not ys:
        return None

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    pad_x = (x_max - x_min) * padding_ratio
    pad_y = (y_max - y_min) * padding_ratio

    return BoundingBox(
        x_min=int(max(0, x_min - pad_x)),
        y_min=int(max(0, y_min - pad_y)),
        x_max=int(min(width, x_max + pad_x)),
        y_max=int(min(height, y_max + pad_y)),
    )


class MediaPipeRegionDetector:
    def __init__(self, landmarker: MediaPipeLandmarker, *, face_crop_margin_px: int) -> None:
        self._landmarker = landmarker
        self._face_crop_margin_px = face_crop_margin_px

    def detect_mouth_and_eyes(
        self, image_bytes: bytes, face_box: BoundingBox, *, image_id: UUID
    ) -> list[DetectedRegion]:
        image = PILImage.open(BytesIO(image_bytes)).convert("RGB")
        crop_box = face_box.expanded(
            self._face_crop_margin_px, image_width=image.width, image_height=image.height
        )
        crop_rgb = np.array(image.crop(crop_box.as_xyxy()))

        landmarks = self._landmarker.detect_face_landmarks(crop_rgb)
        if landmarks is None:
            return []

        regions: list[DetectedRegion] = []
        mouth_box = bbox_from_points(
            landmarks.points,
            _lip_indices(),
            width=landmarks.image_width,
            height=landmarks.image_height,
            padding_ratio=_MOUTH_PADDING_RATIO,
        )
        if mouth_box is not None:
            regions.append(_region_offset_by_crop(image_id, RegionType.MOUTH, mouth_box, crop_box))

        eyes_box = bbox_from_points(
            landmarks.points,
            _eye_indices(),
            width=landmarks.image_width,
            height=landmarks.image_height,
            padding_ratio=_EYES_PADDING_RATIO,
        )
        if eyes_box is not None:
            regions.append(_region_offset_by_crop(image_id, RegionType.EYES, eyes_box, crop_box))

        return regions

    def detect_body(self, image_bytes: bytes, *, image_id: UUID) -> list[DetectedRegion]:
        """Returns BODY (the whole shoulders-to-feet envelope) plus its five
        sub-regions (TORSO, LEFT_ARM, RIGHT_ARM, LEFT_LEG, RIGHT_LEG) from a
        single PoseLandmarker call — the same "coarse region + finer
        sub-regions coexist" pattern as FACE containing MOUTH/EYES. A
        sub-region is silently skipped if its own landmarks are missing,
        rather than failing the whole call."""
        image = PILImage.open(BytesIO(image_bytes)).convert("RGB")
        image_rgb = np.array(image)

        landmarks = self._landmarker.detect_pose_landmarks(image_rgb)
        if landmarks is None:
            return []

        regions: list[DetectedRegion] = []
        for region_type, indices_fn, padding_ratio in _BODY_PART_SPECS:
            box = bbox_from_points(
                landmarks.points,
                indices_fn(),
                width=landmarks.image_width,
                height=landmarks.image_height,
                padding_ratio=padding_ratio,
            )
            if box is not None:
                regions.append(
                    DetectedRegion.new(
                        image_id=image_id,
                        region_type=region_type,
                        bounding_box=box,
                        confidence=_LANDMARK_REGION_CONFIDENCE,
                    )
                )
        return regions


def _region_offset_by_crop(
    image_id: UUID,
    region_type: RegionType,
    crop_local_box: BoundingBox,
    crop_box: BoundingBox,
) -> DetectedRegion:
    """crop_local_box's coordinates are relative to the face crop — offset
    them back to the full image's coordinate space."""
    return DetectedRegion.new(
        image_id=image_id,
        region_type=region_type,
        bounding_box=BoundingBox(
            x_min=crop_local_box.x_min + crop_box.x_min,
            y_min=crop_local_box.y_min + crop_box.y_min,
            x_max=crop_local_box.x_max + crop_box.x_min,
            y_max=crop_local_box.y_max + crop_box.y_min,
        ),
        confidence=_LANDMARK_REGION_CONFIDENCE,
    )
