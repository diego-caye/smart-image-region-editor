from enum import StrEnum


class EditOperation(StrEnum):
    """A structured, predefined transformation the user can apply to a region.

    Users never type a prompt; they pick one of these. Domain only knows the
    *name* of the operation and (via domain/services/region_operation_rules.py)
    which RegionType it is valid for. What it actually means to a specific
    image-editing backend — a Qwen prompt, sampler settings, a reference
    image — is an Infrastructure concern; see
    infrastructure/image_editing/comfyui/operation_prompts.py. Nothing here
    ever leaks into Domain.
    """

    # Hand gestures
    WAVE = "wave"
    PEACE_SIGN = "peace_sign"
    THUMBS_UP = "thumbs_up"
    FIST = "fist"

    # Mouth expressions (RegionType.MOUTH — detector not wired yet in the MVP)
    SMILE = "smile"
    SMILE_WITH_TEETH = "smile_with_teeth"
    CLOSED_MOUTH = "closed_mouth"
