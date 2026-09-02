"""STUB — not implemented yet.

Would score whether the person's identity (face) is preserved across an
edit that touches a *different* region — editing a hand shouldn't alter
who the face looks like. Only meaningful when the edited region is not the
face itself (a face-region edit, e.g. a smile, is expected to change the
face crop somewhat by definition).

Candidate approach: a face-embedding model (e.g. InsightFace/ArcFace —
already partially present on this machine via ComfyUI's insightface
models, though the backend would need its own compatible checkpoint, same
situation as SAM2 vs ComfyUI's copy — see docs/architecture.md) computing
cosine similarity between the face crop in the original and final images.
Not built yet: no face-embedding dependency is installed in the backend,
and it only matters once edits routinely touch non-face regions on photos
where identity fidelity is being graded — not blocking for the MVP.

The interface below is sketched now so a golden-dataset runner can call it
uniformly once implemented, without changing its own shape.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class IdentityPreservationResult:
    similarity: float  # cosine similarity, -1 to 1, higher is more similar
    passed: bool


def evaluate_identity_preservation(
    original_face_crop_png_bytes: bytes,
    final_face_crop_png_bytes: bytes,
    *,
    min_similarity: float = 0.9,
) -> IdentityPreservationResult:
    raise NotImplementedError(
        "identity_preservation evaluation is not implemented yet — see this "
        "module's docstring for the intended approach."
    )
