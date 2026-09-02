"""STUB — not implemented yet.

Would score whether the requested EditOperation actually happened (e.g.
"does this region now show a clear peace sign?"), as opposed to
region_preservation.py's concern (did everything *else* stay the same).

Candidate approach: a vision-language judge (a local Qwen-VL call — the
same model family already running for editing — or a cheap
CLIP-image/text-similarity score) comparing the edited crop against the
operation's own instruction text (see
infrastructure/image_editing/comfyui/operation_prompts.py, so the judge and
the editor share one source of truth for what the operation means). Not
built yet because it needs its own model-selection/calibration pass, which
is out of scope for the MVP's core loop.

The interface below is sketched now so a golden-dataset runner can call it
uniformly once implemented, without changing its own shape.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EditQualityResult:
    score: float  # 0-1, higher is better
    passed: bool
    notes: str


def evaluate_edit_quality(
    edited_region_png_bytes: bytes,
    operation_prompt: str,
    *,
    min_score: float = 0.6,
) -> EditQualityResult:
    raise NotImplementedError(
        "edit_quality evaluation is not implemented yet — see this module's "
        "docstring for the intended approach."
    )
