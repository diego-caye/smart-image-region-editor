"""Thin wrapper around MediaPipe's FaceLandmarker and PoseLandmarker tasks.
Verified against the installed `mediapipe` package's real API — its legacy
`mediapipe.solutions` module is gone as of the installed 1.0.1, replaced by
the Tasks API used here — same discipline as the YOLO/SAM2/ComfyUI
wrappers. Model bundles are downloaded from MediaPipe's own Google Cloud
Storage host (confirmed reachable) on first use and cached; knows nothing
about Domain — adapters/vision/mediapipe_region_detector.py is the
translation layer.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

import numpy as np


def _download_if_missing(dest: Path, url: str) -> Path:
    if dest.is_file():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(dest)
    return dest


class Landmarks:
    """Normalized (0-1) landmark coordinates for one detected face/pose,
    plus the image's own pixel size so callers can convert back to pixel
    coordinates."""

    __slots__ = ("image_height", "image_width", "points")

    def __init__(
        self, points: list[tuple[float, float]], image_width: int, image_height: int
    ) -> None:
        self.points = points
        self.image_width = image_width
        self.image_height = image_height


class MediaPipeLandmarker:
    def __init__(
        self,
        *,
        face_model_path: Path,
        face_model_url: str,
        pose_model_path: Path,
        pose_model_url: str,
    ) -> None:
        self._face_model_path = _download_if_missing(face_model_path, face_model_url)
        self._pose_model_path = _download_if_missing(pose_model_path, pose_model_url)
        self._face_landmarker = None
        self._pose_landmarker = None

    def _get_face_landmarker(self):
        if self._face_landmarker is None:
            from mediapipe.tasks.python import BaseOptions
            from mediapipe.tasks.python.vision import (
                FaceLandmarker,
                FaceLandmarkerOptions,
                RunningMode,
            )

            self._face_landmarker = FaceLandmarker.create_from_options(
                FaceLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(self._face_model_path)),
                    running_mode=RunningMode.IMAGE,
                    num_faces=1,
                )
            )
        return self._face_landmarker

    def _get_pose_landmarker(self):
        if self._pose_landmarker is None:
            from mediapipe.tasks.python import BaseOptions
            from mediapipe.tasks.python.vision import (
                PoseLandmarker,
                PoseLandmarkerOptions,
                RunningMode,
            )

            self._pose_landmarker = PoseLandmarker.create_from_options(
                PoseLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(self._pose_model_path)),
                    running_mode=RunningMode.IMAGE,
                    num_poses=1,
                )
            )
        return self._pose_landmarker

    def detect_face_landmarks(self, image_rgb: np.ndarray) -> Landmarks | None:
        """image_rgb should already be a tight-ish crop around a face —
        MediaPipe's own face detector misses small faces in a full photo,
        verified against a real photo (see docs/architecture.md)."""
        import mediapipe as mp

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        result = self._get_face_landmarker().detect(mp_image)
        if not result.face_landmarks:
            return None
        height, width = image_rgb.shape[:2]
        return Landmarks(
            points=[(lm.x, lm.y) for lm in result.face_landmarks[0]],
            image_width=width,
            image_height=height,
        )

    def detect_pose_landmarks(self, image_rgb: np.ndarray) -> Landmarks | None:
        import mediapipe as mp

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        result = self._get_pose_landmarker().detect(mp_image)
        if not result.pose_landmarks:
            return None
        height, width = image_rgb.shape[:2]
        return Landmarks(
            points=[(lm.x, lm.y) for lm in result.pose_landmarks[0]],
            image_width=width,
            image_height=height,
        )
