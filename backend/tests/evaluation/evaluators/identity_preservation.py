"""Scores whether the face kept its shape across an edit: the face mesh
MediaPipe's FaceLandmarker finds on the original and on the final image,
compared only where the edit wasn't allowed to change anything.

How: detect the 478 landmarks on the same crop around the face in both
images, drop every landmark where the edit dominates the blend (mask at
50% or more, in either image — a smile is supposed to move the mouth;
the feathered rim, mostly original pixels, still counts), align what's left with a
similarity transform (Procrustes: position, scale and rotation don't count
as drift) and report the RMS residual as a fraction of the original's
inter-ocular distance.

What this is and isn't. It catches *geometric* drift: a jaw, nose, brow or
face outline that moved, i.e. the kind of change that makes a face read as
someone else. It does not compare appearance — skin tone, texture or
likeness beyond shape — the way a face-recognition embedding would. The
usual pretrained embedding models (insightface's ArcFace packs, for
example) carry non-commercial licenses, so they aren't used here;
MediaPipe and its face_landmarker model are Apache 2.0, and the backend
already depends on both.

Thresholds are calibrated on real outputs (see docs/architecture.md):
unedited faces and edits outside the face sit far below max_drift, while
the face of a different person sits far above it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image

# Outer corners of the eyes in MediaPipe's face mesh topology.
_LEFT_EYE_OUTER = 263
_RIGHT_EYE_OUTER = 33

# image_rgb (H, W, 3 uint8) -> normalized (x, y) landmarks, or None.
FaceLandmarkFinder = Callable[[np.ndarray], list[tuple[float, float]] | None]


@dataclass(slots=True)
class IdentityPreservationResult:
    applicable: bool  # False when there's no face to compare in the original
    drift: float  # RMS landmark residual / inter-ocular distance; 0 = same shape
    landmarks_compared: int
    passed: bool
    notes: str


def evaluate_identity_preservation(
    original_png_bytes: bytes,
    final_png_bytes: bytes,
    face_box: tuple[int, int, int, int],
    *,
    edited_mask_png_bytes: bytes | None = None,
    mask_threshold: int = 128,
    max_drift: float = 0.03,
    min_landmarks: int = 100,
    context: float = 0.3,
    finder: FaceLandmarkFinder | None = None,
) -> IdentityPreservationResult:
    """face_box is (x_min, y_min, x_max, y_max) in the original image;
    edited_mask_png_bytes, if given, is the full-size mask the edit was
    blended with; pixels at mask_threshold or above count as edited. With
    any value above 0 counting, the 40px grow plus feathering of a mouth
    edit left only 19 of 478 landmarks to compare on a real photo."""
    original = Image.open(BytesIO(original_png_bytes)).convert("RGB")
    final = Image.open(BytesIO(final_png_bytes)).convert("RGB")
    crop = _expanded(face_box, context, original.size)
    find = finder or mediapipe_face_finder()

    before = _pixel_landmarks(find, original, crop)
    if before is None:
        return IdentityPreservationResult(
            False, 0.0, 0, True, "no face found in the original crop — not applicable"
        )
    after = _pixel_landmarks(find, final, crop)
    if after is None:
        return IdentityPreservationResult(
            True, float("inf"), 0, False, "a face was found before the edit but not after it"
        )

    keep = np.ones(len(before), dtype=bool)
    if edited_mask_png_bytes is not None:
        mask = np.asarray(Image.open(BytesIO(edited_mask_png_bytes)).convert("L")) >= mask_threshold
        keep &= ~_inside(mask, before) & ~_inside(mask, after)
    compared = int(keep.sum())
    if compared < min_landmarks:
        return IdentityPreservationResult(
            False,
            0.0,
            compared,
            True,
            f"only {compared} landmarks outside the edit — the edit covers the face",
        )

    interocular = float(np.linalg.norm(before[_LEFT_EYE_OUTER] - before[_RIGHT_EYE_OUTER]))
    drift = _procrustes_rms(before[keep], after[keep]) / interocular
    return IdentityPreservationResult(
        True,
        drift,
        compared,
        drift <= max_drift,
        f"drift {drift:.4f} over {compared} landmarks (max {max_drift})",
    )


def _expanded(
    box: tuple[int, int, int, int], context: float, size: tuple[int, int]
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    dx, dy = (x1 - x0) * context, (y1 - y0) * context
    width, height = size
    return (
        max(0, round(x0 - dx)),
        max(0, round(y0 - dy)),
        min(width, round(x1 + dx)),
        min(height, round(y1 + dy)),
    )


def _pixel_landmarks(
    find: FaceLandmarkFinder, image: Image.Image, crop: tuple[int, int, int, int]
) -> np.ndarray | None:
    """Landmarks in full-image pixel coordinates, found on the crop."""
    region = np.asarray(image.crop(crop))
    points = find(region)
    if points is None:
        return None
    crop_w, crop_h = crop[2] - crop[0], crop[3] - crop[1]
    normalized = np.asarray(points, dtype=np.float64)
    return normalized * [crop_w, crop_h] + [crop[0], crop[1]]


def _inside(mask: np.ndarray, points: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    xs = np.clip(points[:, 0].round().astype(int), 0, width - 1)
    ys = np.clip(points[:, 1].round().astype(int), 0, height - 1)
    return mask[ys, xs]


def _procrustes_rms(source: np.ndarray, target: np.ndarray) -> float:
    """RMS distance left after the best similarity transform (translation,
    uniform scale, rotation) of source onto target, in target's units."""
    src = source - source.mean(axis=0)
    tgt = target - target.mean(axis=0)
    u, singular, vt = np.linalg.svd(src.T @ tgt)
    d = np.sign(np.linalg.det(u @ vt))  # no reflections
    correction = np.diag([1.0, d])
    rotation = u @ correction @ vt
    scale = (singular * np.diag(correction)).sum() / (src**2).sum()
    residual = scale * src @ rotation - tgt
    return float(np.sqrt((residual**2).sum(axis=1).mean()))


_finder_cache: dict[str, FaceLandmarkFinder] = {}


def mediapipe_face_finder() -> FaceLandmarkFinder:
    """The real finder: the same FaceLandmarker bundle the backend's region
    detector uses, from the same cache directory."""
    if "default" not in _finder_cache:
        from app.infrastructure.config.settings import get_settings
        from app.infrastructure.vision.mediapipe_landmarker import MediaPipeLandmarker

        settings = get_settings()
        landmarker = MediaPipeLandmarker(
            face_model_path=settings.models_cache_dir / "mediapipe" / "face_landmarker.task",
            face_model_url=settings.mediapipe_face_landmarker_url,
            pose_model_path=settings.models_cache_dir / "mediapipe" / "pose_landmarker.task",
            pose_model_url=settings.mediapipe_pose_landmarker_url,
        )

        def find(image_rgb: np.ndarray) -> list[tuple[float, float]] | None:
            landmarks = landmarker.detect_face_landmarks(np.ascontiguousarray(image_rgb))
            return landmarks.points if landmarks else None

        _finder_cache["default"] = find
    return _finder_cache["default"]
