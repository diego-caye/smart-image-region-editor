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
    EditOperation.RED_SHIRT: "a photo of a person wearing a red shirt",
    EditOperation.BLACK_JACKET: "a photo of a person wearing a black jacket",
    EditOperation.WHITE_TSHIRT: "a photo of a person wearing a white t-shirt",
    EditOperation.BLUE_JEANS: "a photo of legs wearing blue denim jeans",
    EditOperation.SHORTS: "a photo of legs wearing shorts",
    EditOperation.WRISTWATCH: "a photo of an arm wearing a wristwatch",
    EditOperation.BRACELET: "a photo of an arm wearing a bracelet",
}

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


def candidate_captions(region_type: RegionType) -> list[str]:
    allowed = sorted(operations_allowed_for(region_type), key=lambda op: op.value)
    return [CAPTIONS[op] for op in allowed] + list(_EXTRA_DISTRACTORS.get(region_type, ()))


def evaluate_edit_quality(
    original_region_png_bytes: bytes,
    edited_region_png_bytes: bytes,
    region_type: RegionType,
    operation: EditOperation,
    *,
    min_score: float = 0.5,
    min_gain: float = 0.1,
    scorer: Scorer | None = None,
) -> EditQualityResult:
    """min_gain exists because CLIP is noisy on some unedited crops — it gave
    "an arm wearing a wristwatch" 0.64 on a real arm with no watch — so
    "slightly higher than before" alone would let a no-op edit pass."""
    captions = candidate_captions(region_type)
    if operation not in operations_allowed_for(region_type):
        raise ValueError(f"'{operation}' is not an operation for region '{region_type}'")
    target_index = captions.index(CAPTIONS[operation])

    original = Image.open(BytesIO(original_region_png_bytes)).convert("RGB")
    edited = Image.open(BytesIO(edited_region_png_bytes)).convert("RGB")
    original_probs, edited_probs = (scorer or clip_scorer())([original, edited], captions)

    score = edited_probs[target_index]
    original_score = original_probs[target_index]
    winner = captions[max(range(len(captions)), key=edited_probs.__getitem__)]
    passed = score >= min_score and score - original_score >= min_gain
    notes = (
        f"p(target) {original_score:.2f} -> {score:.2f}; "
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
