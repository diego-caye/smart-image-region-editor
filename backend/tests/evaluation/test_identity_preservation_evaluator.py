"""identity_preservation's geometry, with a fake landmark finder standing in
for MediaPipe — no model, runs in milliseconds. The real finder runs in the
golden dataset (test_golden_dataset.py), where the threshold was calibrated."""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image, ImageDraw

from tests.evaluation.evaluators.identity_preservation import evaluate_identity_preservation

FACE_BOX = (40, 40, 160, 160)
SIZE = (200, 200)
rng = np.random.default_rng(7)
# A made-up face mesh: 478 normalized points, eye corners far apart.
MESH = rng.uniform(0.2, 0.8, size=(478, 2))
MESH[33] = (0.3, 0.4)
MESH[263] = (0.7, 0.4)


def _png(color: str = "gray") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", SIZE, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _finder(*meshes):
    """Returns the given meshes in order, one per call (original, then final)."""
    calls = iter(meshes)

    def find(image_rgb):
        mesh = next(calls)
        return None if mesh is None else [tuple(p) for p in mesh]

    return find


def _evaluate(before, after, **kwargs):
    return evaluate_identity_preservation(
        _png(), _png(), FACE_BOX, finder=_finder(before, after), **kwargs
    )


def test_the_same_face_has_no_drift():
    result = _evaluate(MESH, MESH)
    assert result.passed
    assert result.drift == pytest.approx(0.0, abs=1e-9)
    assert result.landmarks_compared == 478


def test_moving_scaling_or_tilting_the_face_is_not_drift():
    angle = np.deg2rad(8)
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    moved = (MESH - 0.5) @ rotation.T * 0.9 + 0.52
    result = _evaluate(MESH, moved)
    assert result.passed
    assert result.drift == pytest.approx(0.0, abs=1e-9)


def test_a_reshaped_face_fails():
    reshaped = MESH + rng.normal(0, 0.03, size=MESH.shape)
    result = _evaluate(MESH, reshaped)
    assert not result.passed
    assert result.drift > 0.03


def test_landmarks_inside_the_edited_area_are_not_compared():
    # everything in the top half of the crop moves; the mask covers it
    moved = MESH.copy()
    moved[MESH[:, 1] < 0.5] += 0.05
    mask = Image.new("L", SIZE, 0)
    ImageDraw.Draw(mask).rectangle((0, 0, SIZE[0], 100), fill=255)
    buffer = io.BytesIO()
    mask.save(buffer, format="PNG")

    unmasked = _evaluate(MESH, moved, min_landmarks=10)
    masked = _evaluate(MESH, moved, edited_mask_png_bytes=buffer.getvalue(), min_landmarks=10)

    assert not unmasked.passed
    assert masked.passed
    assert masked.landmarks_compared < 478


def test_a_face_lost_in_the_edit_fails():
    result = _evaluate(MESH, None)
    assert result.applicable
    assert not result.passed


def test_no_face_in_the_original_is_not_applicable():
    result = _evaluate(None, MESH)
    assert not result.applicable
    assert result.passed
