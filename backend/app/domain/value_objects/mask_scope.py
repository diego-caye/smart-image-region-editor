from __future__ import annotations

from enum import StrEnum


class MaskScope(StrEnum):
    """How much of a region an edit may change. Most edits get the whole
    region; a garment worn *under* something (a T-shirt under an open
    jacket) gets only its own visible part, so whatever is worn over it
    can't change — by construction, not by asking the model nicely."""

    WHOLE_REGION = "whole_region"
    INNER_LAYER = "inner_layer"
