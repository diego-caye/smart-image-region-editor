"""edit_quality's decision logic, with a fake scorer standing in for CLIP —
no model download, runs in milliseconds. The real CLIP scorer is exercised
by the opt-in test_edit_quality_live.py."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor
from app.domain.value_objects.region_type import RegionType
from tests.evaluation.evaluators.edit_quality import (
    CAPTIONS,
    candidate_captions,
    caption_for,
    color_captions,
    evaluate_edit_quality,
)


def _png(color: str) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _fake_scorer(original_target: float, edited_target: float, *target_captions: str):
    """Gives each target caption the requested probability on each image
    and spreads the rest evenly over the other candidates."""

    def score(images, captions):
        rows = []
        for p_target in (original_target, edited_target):
            rest = (1 - p_target) / (len(captions) - 1)
            rows.append([p_target if c in target_captions else rest for c in captions])
        return rows

    return score


def test_every_operation_has_a_caption():
    assert set(CAPTIONS) == set(EditOperation)


def test_candidates_are_the_region_own_operations():
    # PANTS_COLOR only recolors, so it isn't a garment type of its own
    captions = candidate_captions(RegionType.LEGS)
    assert captions == [caption_for(EditOperation.BLUE_JEANS), caption_for(EditOperation.SHORTS)]


def test_arms_also_compete_against_no_accessory():
    # with only watch vs bracelet, one would always "win" on an untouched arm
    assert len(candidate_captions(RegionType.LEFT_ARM)) == 3


def test_passes_when_the_edit_moves_clip_toward_the_target():
    target = caption_for(EditOperation.PEACE_SIGN)
    result = evaluate_edit_quality(
        _png("gray"),
        _png("white"),
        RegionType.RIGHT_HAND,
        EditOperation.PEACE_SIGN,
        scorer=_fake_scorer(0.1, 0.8, target),
    )
    assert result.passed
    assert result.score == pytest.approx(0.8)
    assert result.original_score == pytest.approx(0.1)


def test_fails_when_the_target_was_already_as_likely_before_the_edit():
    # e.g. the model returned the crop essentially unchanged
    target = caption_for(EditOperation.BLUE_JEANS)
    result = evaluate_edit_quality(
        _png("gray"),
        _png("gray"),
        RegionType.LEGS,
        EditOperation.BLUE_JEANS,
        scorer=_fake_scorer(0.7, 0.7, target),
    )
    assert not result.passed


def test_fails_on_a_gain_too_small_to_tell_apart_from_clip_noise():
    # a real unedited arm already scored 0.64 for "wristwatch"
    target = caption_for(EditOperation.WRISTWATCH)
    result = evaluate_edit_quality(
        _png("gray"),
        _png("gray"),
        RegionType.RIGHT_ARM,
        EditOperation.WRISTWATCH,
        scorer=_fake_scorer(0.64, 0.68, target),
    )
    assert not result.passed


def test_fails_when_the_target_is_still_unlikely_after_the_edit():
    target = caption_for(EditOperation.SHIRT_COLOR, GarmentColor.RED)
    result = evaluate_edit_quality(
        _png("gray"),
        _png("white"),
        RegionType.TORSO,
        EditOperation.SHIRT_COLOR,
        color=GarmentColor.RED,
        scorer=_fake_scorer(0.05, 0.3, target),
    )
    assert not result.passed


def test_a_recolor_is_scored_against_every_palette_color_only():
    red_shirt = caption_for(EditOperation.SHIRT_COLOR, GarmentColor.RED)
    seen = []

    def scorer(images, captions):
        seen.append(list(captions))
        return _fake_scorer(0.1, 0.8, red_shirt)(images, captions)

    result = evaluate_edit_quality(
        _png("gray"),
        _png("red"),
        RegionType.TORSO,
        EditOperation.SHIRT_COLOR,
        color=GarmentColor.RED,
        scorer=scorer,
    )
    assert result.passed
    assert seen == [color_captions(EditOperation.SHIRT_COLOR)]


def test_a_new_colored_garment_must_get_both_the_color_and_the_type_right():
    red_hoodie = caption_for(EditOperation.HOODIE, GarmentColor.RED)
    hoodie = caption_for(EditOperation.HOODIE)

    def evaluate(scorer):
        return evaluate_edit_quality(
            _png("gray"),
            _png("red"),
            RegionType.TORSO,
            EditOperation.HOODIE,
            color=GarmentColor.RED,
            scorer=scorer,
        )

    assert not evaluate(_fake_scorer(0.1, 0.8, red_hoodie)).passed
    assert evaluate(_fake_scorer(0.1, 0.8, red_hoodie, hoodie)).passed


def test_rejects_an_operation_that_does_not_belong_to_the_region():
    with pytest.raises(ValueError):
        evaluate_edit_quality(
            _png("gray"), _png("gray"), RegionType.LEGS, EditOperation.PEACE_SIGN
        )
