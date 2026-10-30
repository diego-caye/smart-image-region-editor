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

    # Mouth expressions
    SMILE = "smile"
    SMILE_WITH_TEETH = "smile_with_teeth"
    CLOSED_MOUTH = "closed_mouth"

    # Eyes
    OPEN_EYES = "open_eyes"
    CLOSED_EYES = "closed_eyes"

    # Upper-body garments (torso)
    RED_SHIRT = "red_shirt"
    BLACK_JACKET = "black_jacket"
    WHITE_TSHIRT = "white_tshirt"

    # Lower-body garments (both legs)
    BLUE_JEANS = "blue_jeans"
    SHORTS = "shorts"

    # Arm accessories
    WRISTWATCH = "wristwatch"
    BRACELET = "bracelet"
