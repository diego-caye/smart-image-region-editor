"""Sanity-checks the real CLIP scorer on an unedited photo with a known
answer: the waving man's raised hand should be classified as "wave" among
the hand operations. Catches a broken model download, a processor API
change, or captions that CLIP can't tell apart — without needing ComfyUI.
Opt-in (`pytest -m live_models`): downloads CLIP (~600MB) and the photo.
"""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.region_type import RegionType
from tests.evaluation.dataset_images import all_entries, ensure_image, square_crop
from tests.evaluation.evaluators.edit_quality import CAPTIONS, candidate_captions, clip_scorer

pytestmark = pytest.mark.live_models


def test_clip_recognizes_an_unedited_waving_hand_as_wave():
    entry = next(e for e in all_entries() if e["id"] == "waving-man-right-hand-peace-sign")
    image_bytes = ensure_image(entry).read_bytes()
    crop = square_crop(image_bytes, BoundingBox(*entry["region_box"]))

    captions = candidate_captions(RegionType.RIGHT_HAND)
    (probs,) = clip_scorer()([Image.open(BytesIO(crop)).convert("RGB")], captions)

    by_caption = dict(zip(captions, probs, strict=True))
    assert max(by_caption, key=by_caption.get) == CAPTIONS[EditOperation.WAVE], by_caption
