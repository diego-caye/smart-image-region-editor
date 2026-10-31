"""Scores whether the requested EditOperation actually happened ("does this
hand now show a peace sign?"), as opposed to region_preservation.py's
concern (did everything *else* stay the same).

Zero-shot CLIP classification among the operations the domain allows on
that region type (region_operation_rules.py — the same source of truth the
UI's gallery uses): the edited crop must be classified as the requested
operation, and more confidently than the original crop was. Comparing
against the original is what makes the score mean "the edit moved toward
the target" rather than "this photo already looked a bit like that".

Captions live here rather than reusing operation_prompts.py: those are
instructions for an editor ("Change the hand gesture to..."), while CLIP is
trained on image captions ("a photo of a hand making a peace sign") and
scores those far more reliably.

Operations that take a GarmentColor are scored on two axes, and must pass
both: the color (the caption in the requested color against the same
caption in every other palette color) and, unless the operation only
recolors, the garment type (as above, among the region's garments). Either
axis alone lets a wrong edit through: a red jacket where a red hoodie was
asked, or a blue hoodie where a red one was.

Runs on CPU on purpose — CLIP ViT-B/32 is small enough, and it keeps the
evaluator from competing for VRAM with ComfyUI or anything else on the GPU.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from io import BytesIO

from PIL import Image

from app.domain.services.region_operation_rules import operations_allowed_for
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor
from app.domain.value_objects.region_type import RegionType

CLIP_MODEL_ID = "openai/clip-vit-base-patch32"

CAPTIONS: dict[EditOperation, str] = {
    EditOperation.WAVE: "a photo of an open hand waving hello",
    EditOperation.PEACE_SIGN: "a photo of a hand making a peace sign with two fingers",
    EditOperation.THUMBS_UP: "a photo of a hand giving a thumbs up",
    EditOperation.FIST: "a photo of a closed fist",
    EditOperation.SMILE: "a photo of a mouth with a closed-lip smile",
    EditOperation.SMILE_WITH_TEETH: "a photo of a wide smile showing teeth",
    EditOperation.CLOSED_MOUTH: "a photo of a neutral closed mouth",
    EditOperation.OPEN_EYES: "a photo of wide open eyes",
    EditOperation.CLOSED_EYES: "a photo of closed eyes",
    EditOperation.SUNGLASSES: "a photo of eyes covered by dark sunglasses",
    EditOperation.GLOVES: "a photo of a hand wearing a glove",
    # {color} is filled with "red " etc., or "" when scoring the garment type
    EditOperation.SHIRT_COLOR: "a photo of a person wearing a {color}shirt",
    EditOperation.T_SHIRT: "a photo of a person wearing a {color}t-shirt",
    EditOperation.JACKET: "a photo of a person wearing a {color}jacket",
    EditOperation.HOODIE: "a photo of a person wearing a {color}hoodie",
    EditOperation.BLUE_JEANS: "a photo of legs wearing blue denim jeans",
    EditOperation.PANTS_COLOR: "a photo of legs wearing {color}pants",
    EditOperation.SHORTS: "a photo of legs wearing {color}shorts",
    EditOperation.WRISTWATCH: "a photo of an arm wearing a wristwatch",
    EditOperation.BRACELET: "a photo of an arm wearing a bracelet",
}

# Only change a color, not what's worn: no garment-type axis, and not a
# garment-type candidate for the region's other operations either.
_RECOLOR_ONLY = frozenset({EditOperation.SHIRT_COLOR, EditOperation.PANTS_COLOR})

# With only two candidate operations, one of them always wins a two-way
# softmax even on an untouched arm, so arms also compete against "neither".
_EXTRA_DISTRACTORS: dict[RegionType, tuple[str, ...]] = {
    RegionType.LEFT_ARM: ("a photo of a bare wrist with no watch or bracelet",),
    RegionType.RIGHT_ARM: ("a photo of a bare wrist with no watch or bracelet",),
}

# (images, captions) -> one probability row per image, each summing to 1
# across the captions.
Scorer = Callable[[Sequence[Image.Image], Sequence[str]], list[list[float]]]


@dataclass(slots=True)
class EditQualityResult:
    score: float  # probability CLIP assigns the target operation on the edited crop
    original_score: float  # same, on the original crop
    passed: bool
    notes: str


def caption_for(operation: EditOperation, color: GarmentColor | None = None) -> str:
    return CAPTIONS[operation].format(color=f"{color} " if color else "")


def candidate_captions(region_type: RegionType) -> list[str]:
    allowed = sorted(operations_allowed_for(region_type) - _RECOLOR_ONLY, key=lambda op: op.value)
    return [caption_for(op) for op in allowed] + list(_EXTRA_DISTRACTORS.get(region_type, ()))


def color_captions(operation: EditOperation) -> list[str]:
    return [caption_for(operation, color) for color in GarmentColor]


def evaluate_edit_quality(
    original_region_png_bytes: bytes,
    edited_region_png_bytes: bytes,
    region_type: RegionType,
    operation: EditOperation,
    *,
    color: GarmentColor | None = None,
    min_score: float = 0.5,
    min_gain: float = 0.1,
    scorer: Scorer | None = None,
) -> EditQualityResult:
    """min_gain exists because CLIP is noisy on some unedited crops — it gave
    "an arm wearing a wristwatch" 0.64 on a real arm with no watch — so
    "slightly higher than before" alone would let a no-op edit pass."""
    if operation not in operations_allowed_for(region_type):
        raise ValueError(f"'{operation}' is not an operation for region '{region_type}'")

    axes: list[tuple[str, list[str], str]] = []  # (name, candidates, target)
    if color is not None:
        axes.append(("color", color_captions(operation), caption_for(operation, color)))
    if operation not in _RECOLOR_ONLY:
        axes.append(("type", candidate_captions(region_type), caption_for(operation)))

    images = [
        Image.open(BytesIO(png)).convert("RGB")
        for png in (original_region_png_bytes, edited_region_png_bytes)
    ]
    score_images = scorer or clip_scorer()
    results = [
        _score_axis(score_images, images, name, captions, target, min_score, min_gain)
        for name, captions, target in axes
    ]
    weakest = min(results, key=lambda r: r.score)
    return EditQualityResult(
        score=weakest.score,
        original_score=weakest.original_score,
        passed=all(r.passed for r in results),
        notes=" | ".join(r.notes for r in results),
    )


def _score_axis(
    scorer: Scorer,
    images: list[Image.Image],
    name: str,
    captions: list[str],
    target: str,
    min_score: float,
    min_gain: float,
) -> EditQualityResult:
    target_index = captions.index(target)
    original_probs, edited_probs = scorer(images, captions)
    score = edited_probs[target_index]
    original_score = original_probs[target_index]
    winner = captions[max(range(len(captions)), key=edited_probs.__getitem__)]
    passed = score >= min_score and score - original_score >= min_gain
    notes = (
        f"{name}: p(target) {original_score:.2f} -> {score:.2f}; "
        f"edited crop's top caption: '{winner}'"
    )
    return EditQualityResult(
        score=score, original_score=original_score, passed=passed, notes=notes
    )


_clip_cache: dict[str, tuple] = {}


def clip_scorer(model_id: str = CLIP_MODEL_ID) -> Scorer:
    """The real scorer. Uses the full forward pass (logits_per_image) rather
    than get_image_features/get_text_features, whose return type changed in
    transformers 5 (a model output object instead of a tensor)."""
    import torch
    from transformers import CLIPModel, CLIPProcessor

    if model_id not in _clip_cache:
        _clip_cache[model_id] = (
            CLIPModel.from_pretrained(model_id).eval(),
            CLIPProcessor.from_pretrained(model_id),
        )
    model, processor = _clip_cache[model_id]

    def score(images: Sequence[Image.Image], captions: Sequence[str]) -> list[list[float]]:
        inputs = processor(
            text=list(captions), images=list(images), return_tensors="pt", padding=True
        )
        with torch.inference_mode():
            logits = model(**inputs).logits_per_image
        return logits.softmax(dim=-1).tolist()

    return score
